using System;
using Joy.Api;

namespace JoyGame
{
    /// <summary>
    /// 运行期资源句柄，全部走生成链路（Joy.Api.Bindings → Joy.Api 强句柄）。
    /// 图片改用全标量版 ImageCreate / ImageDrawRect：绕开 joy_rect_t* 无法进
    /// joy_value 的 L3 限制；图片缺失时 Painter.Sprite 退回同尺寸色块。
    /// </summary>
    internal sealed class Assets
    {
        // 仓内只保留含中文字形的字体。早先随模板分发的 ARIALNB.TTF 及 Arial 系列变体
        // 只有拉丁字形，中文码点查不到字形会落到 .notdef，渲染成豆腐块/乱码，已全部移除。
        // 底层 jfont.c 用 stbtt_InitFont(data, 0)，只稳妥支持 TrueType glyf 轮廓的
        // 单字体 .ttf，不要放 .ttc 字体集合或 CFF 轮廓的 .otf。
        // simsunb.ttf 是宋体扩展汉字补充，不保证覆盖常用字，故不列入 UI 字体候选。
        private static readonly string[] CjkFonts =
        {
            "fonts/simhei.ttf",       // 仓内自带黑体，首选（模板自包含）
            "C:/Windows/Fonts/simhei.ttf",   // 系统兜底
            "C:/Windows/Fonts/Deng.ttf",
        };

        public Image PlayerImage { get; private set; }
        public Image EnemyImage { get; private set; }

        // ImageCreate 在底层返回 NULL 时抛 InvalidOperationException（与 FontCreate 同约定），
        // 贴图缺失时返回 null，让 Painter.Sprite 走色块而不是中断游戏。
        private static Image TryImage(Jr2d r2d, string path)
        {
            try { return Bindings.ImageCreate(r2d, path); }
            catch (InvalidOperationException) { return null; }
        }

        public Font FontSmall { get; private set; }
        public Font FontBig { get; private set; }

        /// <summary>是否成功加载到含中文字形的字体；界面文案据此选择中文或 ASCII 兜底。</summary>
        public bool HasCjkFont { get; private set; }

        public float PlayerW { get; private set; } = 16f;
        public float PlayerH { get; private set; } = 16f;
        public float EnemyW { get; private set; } = 16f;
        public float EnemyH { get; private set; } = 16f;

        public void Load(Jr2d r2d)
        {
            // FontCreate 在底层返回 NULL 时抛 InvalidOperationException（生成代码的约定），
            // 逐个候选 try 一次即可，命中后两个字号共用同一路径。
            foreach (string path in CjkFonts)
            {
                try
                {
                    Font small = Bindings.FontCreate(path, 12);
                    FontSmall = small;
                    FontBig = Bindings.FontCreate(path, 22);
                    HasCjkFont = true;
                    break;
                }
                catch (InvalidOperationException)
                {
                    FontSmall = null;
                    FontBig = null;
                }
            }

            PlayerImage = TryImage(r2d, "sprites/player.png");
            EnemyImage = TryImage(r2d, "sprites/enemy.png");

            if (FontSmall == null) Joy.Host.log("[warn] no usable font, HUD text disabled");
        }
    }
}
