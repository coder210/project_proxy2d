#include "clr_host.h"

#include <SDL3/SDL.h>
#include <SDL3/SDL_loadso.h>
#include <joy/joy.h>
#include "third_party/joy/modules/cs/joy_csharp.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#if defined(_WIN32)
#  include <direct.h>
#else
#  include <unistd.h>
#endif

/* ---- C# 宿主状态（与 joy examples/csharp_host 同一套入口契约）---- */
static csx_p        s_csx = NULL;
static csx_method_p s_on_init = NULL;
static csx_method_p s_on_frame = NULL;
static csx_method_p s_on_shutdown = NULL;

static int    s_smoke_frames = 0;
static int    s_frame = 0;
static Uint64 s_last_tick_ns = 0;
static bool   s_ready = false;
static const char* s_assembly = "JoyGame.dll";

static const int APP_W = 480;
static const int APP_H = 320;

static int find_arg(int argc, char* argv[], const char* name)
{
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], name) == 0) return i;
    return -1;
}

/* 把 CWD 对齐到 exe 目录：JoyGame.dll / lib/ / fonts/ / sprites/ 都是相对路径，
 * 从仓库根或 IDE 启动时若不对齐，MONO_LIB_DIR="lib" 会解析到错误目录，
 * CLR 因找不到 CoreLib 而启动失败。 */
static void align_working_dir(const char* argv0)
{
    if (!argv0 || !*argv0) return;
    const char* sep = NULL;
    for (const char* p = argv0; *p; ++p)
        if (*p == '/' || *p == '\\') sep = p;
    if (!sep) return; // 经 PATH 启动，CWD 通常已是资源根
    size_t n = (size_t)(sep - argv0);
    if (n == 0 || n >= 1024) return;
    char dir[1024];
    std::memcpy(dir, argv0, n);
    dir[n] = '\0';
#if defined(_WIN32)
    (void)_chdir(dir);
#else
    (void)chdir(dir);
#endif
}

static bool setup_clr_dirs()
{
#if defined(_WIN32)
    _putenv_s("MONO_LIB_DIR", "lib");
#else
    setenv("MONO_LIB_DIR", "lib", 1);

    /* Linux/macOS 的 CoreLib P/Invoke 目标拆成独立 shim，libcoreclr 无 RUNPATH，
     * dlopen 不搜 exe 目录；按带 "./" 的相对路径预加载（CWD 已对齐 exe 目录），
     * 缺失的忽略。清单与 runtimes/<platform>/ 入库的 libSystem.* 一致。 */
    static const char* const kClrShims[] = {
        "libSystem.Native.so", "libSystem.Native.dylib",
        "libSystem.Globalization.Native.so", "libSystem.Globalization.Native.dylib",
        "libSystem.IO.Compression.Native.so", "libSystem.IO.Compression.Native.dylib",
        "libSystem.Net.Security.Native.so", "libSystem.Net.Security.Native.dylib",
        "libSystem.Security.Cryptography.Native.OpenSsl.so",
        "libSystem.Security.Cryptography.Native.OpenSsl.dylib",
        "libSystem.Security.Cryptography.Native.Apple.dylib",
        NULL
    };
    for (int i = 0; kClrShims[i]; ++i) {
        char path[512];
        std::snprintf(path, sizeof(path), "./%s", kClrShims[i]);
        if (!SDL_LoadObject(path)) SDL_ClearError();
    }
#endif
    return true;
}

bool clr_host_init(int argc, char* argv[])
{
    align_working_dir(argc > 0 ? argv[0] : NULL);
    if (!setup_clr_dirs()) return false;

    int i = find_arg(argc, argv, "--smoke");
    if (i >= 0 && i + 1 < argc) s_smoke_frames = std::atoi(argv[i + 1]);
    i = find_arg(argc, argv, "--assembly");
    if (i >= 0 && i + 1 < argc) s_assembly = argv[i + 1];

    /* 不覆盖平台/驱动默认：视频与渲染后端由 SDL 默认或环境变量决定。
     * 无头环境（CI）由调用方设 SDL_VIDEODRIVER。 */
    if (s_smoke_frames <= 0) {
        SDL_SetHint(SDL_HINT_MAIN_CALLBACK_RATE, "60");
    }

    /* SDL 子系统由宿主显式初始化并逐项打日志：窗口由 C# 侧创建，
     * 无头环境下出问题时能看出卡在哪个子系统。 */
    {
        static const struct {
            const char  *name;
            SDL_InitFlags flag;
            bool         required;
        } kSteps[] = {
            { "VIDEO",    SDL_INIT_VIDEO,    true  },
            { "EVENTS",   SDL_INIT_EVENTS,   true  },
            { "AUDIO",    SDL_INIT_AUDIO,    false },
            { "JOYSTICK", SDL_INIT_JOYSTICK, false },
        };
        for (size_t k = 0; k < SDL_arraysize(kSteps); ++k) {
            SDL_Log("[host] SDL init %s ...", kSteps[k].name);
            if (!SDL_InitSubSystem(kSteps[k].flag)) {
                SDL_Log("[host] SDL init %s FAILED: %s", kSteps[k].name, SDL_GetError());
                if (kSteps[k].required) return false;
            }
        }
    }

    SDL_Log("[cs] creating CoreCLR, assembly=%s", s_assembly);
    s_csx = csx_create();
    if (!s_csx) {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION, "[cs] csx_create failed");
        return false;
    }
    if (!csx_load_assembly(s_csx, s_assembly)) {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION, "[cs] load assembly failed: %s", s_assembly);
        return false;
    }

    /* 入口契约见 joy modules/cs/joy_cs_entry.h：JoyGame.JoyEntry.OnInit/OnFrame/OnShutdown */
    s_on_init = csx_find_method(s_csx, "JoyGame", "JoyEntry", "OnInit", 3);
    s_on_frame = csx_find_method(s_csx, "JoyGame", "JoyEntry", "OnFrame", 1);
    s_on_shutdown = csx_find_method(s_csx, "JoyGame", "JoyEntry", "OnShutdown", 0);
    if (!s_on_init || !s_on_frame || !s_on_shutdown) {
        SDL_LogError(SDL_LOG_CATEGORY_APPLICATION, "[cs] JoyEntry methods not found");
        return false;
    }

    {
        int w = APP_W, h = APP_H, smoke = s_smoke_frames;
        void* args[3] = { &w, &h, &smoke };
        SDL_Log("[host] calling C# JoyEntry.OnInit(w=%d,h=%d,smoke=%d)", w, h, smoke);
        csx_invoke_method(s_csx, s_on_init, args);
    }

    s_last_tick_ns = SDL_GetTicksNS();
    s_ready = true;
    SDL_Log("[cs] CoreCLR ready");
    return true;
}

SDL_AppResult clr_host_event(SDL_Event* e)
{
    if (!s_ready) return SDL_APP_CONTINUE;
    switch (e->type) {
    case SDL_EVENT_KEY_DOWN:
        csx_input_key((int)e->key.scancode, true);
        break;
    case SDL_EVENT_KEY_UP:
        csx_input_key((int)e->key.scancode, false);
        break;
    case SDL_EVENT_MOUSE_MOTION:
        csx_input_mouse_move(e->motion.x, e->motion.y);
        break;
    case SDL_EVENT_MOUSE_BUTTON_DOWN:
        csx_input_mouse_button((int)e->button.button, true);
        break;
    case SDL_EVENT_MOUSE_BUTTON_UP:
        csx_input_mouse_button((int)e->button.button, false);
        break;
    case SDL_EVENT_MOUSE_WHEEL:
        csx_input_wheel(e->wheel.y);
        break;
    case SDL_EVENT_QUIT:
        return SDL_APP_SUCCESS;
    default:
        break;
    }
    return SDL_APP_CONTINUE;
}

SDL_AppResult clr_host_iterate()
{
    if (!s_ready) return SDL_APP_FAILURE;

    float dt;
    if (s_smoke_frames > 0) {
        dt = 1.0f / 60.0f;
    } else {
        Uint64 now = SDL_GetTicksNS();
        dt = (float)((double)(now - s_last_tick_ns) / (double)SDL_NS_PER_SECOND);
        s_last_tick_ns = now;
        if (dt < 0.0f) dt = 0.0f;
        if (dt > 0.1f) dt = 0.1f;
    }

    {
        void* args[1] = { &dt };
        csx_invoke_method(s_csx, s_on_frame, args);
    }
    csx_input_end_frame();

    s_frame++;
    if (s_smoke_frames > 0 && s_frame >= s_smoke_frames) {
        std::printf("[cs] smoke finished: frames=%d exit=%d\n", s_frame, csx_host_exit_code());
        std::fflush(stdout);
        return csx_host_exit_code() == 0 ? SDL_APP_SUCCESS : SDL_APP_FAILURE;
    }
    if (csx_host_quit_requested())
        return csx_host_exit_code() == 0 ? SDL_APP_SUCCESS : SDL_APP_FAILURE;
    return SDL_APP_CONTINUE;
}

void clr_host_quit()
{
    if (s_csx && s_on_shutdown) csx_invoke_method(s_csx, s_on_shutdown, NULL);
    if (s_on_init) csx_method_free(s_on_init);
    if (s_on_frame) csx_method_free(s_on_frame);
    if (s_on_shutdown) csx_method_free(s_on_shutdown);
    if (s_csx) csx_release(s_csx);
    s_csx = NULL;
    s_ready = false;
}

bool clr_host_quit_requested()
{
    return s_ready && csx_host_quit_requested();
}

int clr_host_exit_code()
{
    return csx_host_exit_code();
}
