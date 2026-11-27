using System;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;

namespace JoyGame
{
    /// <summary>
    /// native 宿主与 C# 之间的唯一入口边界。
    ///
    /// 桌面：hostfxr 通过 load_assembly_and_get_function_pointer 取 UCO 方法指针；
    /// Android：mono_runtime_invoke 不能调 UCO，取同名 + Mono 后缀的普通方法。
    /// 两套入口都只是薄壳，业务逻辑在 Mono 版本里，保证只有一份实现。
    /// </summary>
    public static class JoyEntry
    {
        private static GameApp _app;
        private static SmokeScript _smoke;

        // ---- 绑定初始化入口 ----

        [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
        public static void Bootstrap(IntPtr lookupFn)
        {
            BootstrapMono(lookupFn);
        }

        public static void BootstrapMono(IntPtr lookupFn)
        {
            Joy.NativeFuncs.Initialize(lookupFn);
        }

        // ---- 游戏生命周期入口 ----

        [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
        public static void OnInit(int width, int height, int smokeFrames)
        {
            OnInitMono(width, height, smokeFrames);
        }

        [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
        public static void OnFrame(float dt)
        {
            OnFrameMono(dt);
        }

        [UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
        public static void OnShutdown()
        {
            OnShutdownMono();
        }

        // ---- 共享实现（桌面 UCO 薄壳 + Android Mono 入口） ----

        public static void OnInitMono(int width, int height, int smokeFrames)
        {
            // SDL 子系统必须显式初始化：窗口由托管侧经 Joy.Api.Bindings 创建。
            // SDL_Init 是引用计数的，Android 原生侧若已初始化过也可安全重复调用。
            if (!Joy.Api.Bindings.InitEnv())
            {
                Joy.Host.log("[host] SDL init failed, SDL_VIDEODRIVER=" +
                             (Environment.GetEnvironmentVariable("SDL_VIDEODRIVER") ?? "<unset>"));
            }
            _app = new GameApp(width, height, smokeFrames);
            _smoke = smokeFrames > 0 ? new SmokeScript() : null;
            if (smokeFrames > 0) ApiBindingSmoke.Run();
            _app.Start();
            Joy.Host.log("[host] init " + width + "x" + height +
                         (smokeFrames > 0 ? " smoke=" + smokeFrames : ""));
        }

        public static void OnFrameMono(float dt)
        {
            if (_app == null) return;
            _smoke?.BeforeTick(_app);
            _app.Tick(dt);
            _smoke?.AfterTick(_app);
        }

        public static void OnShutdownMono()
        {
            Joy.Host.log("[host] shutdown frames=" + (_app != null ? _app.Frame : 0));
        }
    }
}
