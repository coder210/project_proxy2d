#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL_main.h>
#include <SDL3/SDL.h>
#include "clr_host.h"

// 纯 C# 2D 瘦入口：窗口 / r2d 渲染 / 玩法 / 场景全部在 JoyGame.dll 中，
// 本宿主只负责 CoreCLR 启动、SDL 事件转发与帧回调。
extern "C" SDL_AppResult SDL_AppInit(void** appstate, int argc, char* argv[]) {
    (void)appstate;
    return clr_host_init(argc, argv) ? SDL_APP_CONTINUE : SDL_APP_FAILURE;
}

extern "C" SDL_AppResult SDL_AppEvent(void* appstate, SDL_Event* e) {
    (void)appstate;
    return clr_host_event(e);
}

extern "C" SDL_AppResult SDL_AppIterate(void* appstate) {
    (void)appstate;
    return clr_host_iterate();
}

extern "C" void SDL_AppQuit(void* appstate, SDL_AppResult result) {
    (void)appstate;
    (void)result;
    clr_host_quit();
}
