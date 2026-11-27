using System;
using Joy.Api;

namespace JoyGame
{
    /// <summary>
    /// 应用外壳：持有窗口/渲染句柄、资源、输入快照与当前场景。
    /// 每帧由宿主的 C# 入口 JoyEntry.OnFrame 驱动 Tick。
    ///
    /// 窗口与渲染器由本类自己通过生成链路（Joy.Api.Bindings）创建，
    /// 宿主不再建——生成链路用句柄表管理对象，宿主的裸指针不在表里。
    /// </summary>
    internal sealed class GameApp
    {
        public Jwindow Window { get; }
        public Jr2d R2d { get; }
        public int Width { get; }
        public int Height { get; }
        public int SmokeFrames { get; }

        public Assets Assets { get; } = new Assets();
        public InputState Input { get; } = new InputState();
        /// <summary>与 cpp / lua / js 三份示例同算法同种子，见 Rng.cs。</summary>
        public Rng Rng { get; } = new Rng(12345u);

        public IScene Scene { get; private set; }
        public int Frame { get; private set; }

        public bool Smoke => SmokeFrames > 0;

        public GameApp(int width, int height, int smokeFrames)
        {
            Width = width;
            Height = height;
            SmokeFrames = smokeFrames;

            Window = Bindings.CreateWindow("project_proxy2d", width, height);
            R2d = Bindings.R2dCreate(Window);
            // 对齐 joy_topdown_template/logical_presentation.h 的 presentation_set_design：
            // joy_r2d_create 默认用窗口物理尺寸 + STRETCH，Android 全屏下 480x320 只占一角；
            // 覆盖为固定设计分辨率 + LETTERBOX（等比缩放居中、不拉伸）。
            // 2 == JOY_LOGICAL_PRESENTATION_LETTERBOX（见 include/joy/jdefs.h）
            Bindings.R2dSetLogicalPresentationMode(R2d, width, height, 2);
        }

        public void Start()
        {
            Assets.Load(R2d);
            ChangeScene(new MenuScene());
        }

        public void ChangeScene(IScene next)
        {
            Scene = next;
            next.Enter(this);
        }

        public void Tick(float dt)
        {
            if (dt < 0f) dt = 0f;
            if (dt > 0.05f) dt = 0.05f;

            Frame++;
            Input.BeginFrame();
            Scene.Update(dt);

            // R2dBegin 用当前颜色清屏，先铺底色再让场景自己画满
            Bindings.R2dSetColorf(R2d, 0.06f, 0.07f, 0.10f, 1f);
            Bindings.R2dBegin(R2d);
            Scene.Render();
            Bindings.R2dEnd(R2d);
        }
    }
}
