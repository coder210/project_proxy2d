using System;
using System.Text;
using Joy.Api;

namespace JoyGame
{
    /// <summary>
    /// C# 侧的绘制门面，全部走生成链路（Joy.Api.Bindings）。
    ///
    /// 生成链路里 R2dSetColorf 是「设当前色」，ShapeDrawRectangle / ShapeDrawLine
    /// 都用这个当前色，所以每个绘制函数先设色再画。
    /// *_f 系列（ShapeDrawLineF 等）参数是归一化比例，会乘窗口宽高；这里所有
    /// 坐标都是像素，故一律用非 _f 版本。
    /// 文字宽度测量（joy_r2d_text_measurex）是 L3 的输出参数，尚未开放，居中用估算。
    /// </summary>
    internal static class Painter
    {
        public static void Fill(GameApp app, float x, float y, float w, float h,
                                int r, int g, int b, int a = 255)
        {
            Bindings.R2dSetColorf(app.R2d, r / 255f, g / 255f, b / 255f, a / 255f);
            Bindings.ShapeDrawRectangle(app.R2d, "fill", x, y, w, h);
        }

        public static void Stroke(GameApp app, float x, float y, float w, float h,
                                  int r, int g, int b, int a = 255)
        {
            Bindings.R2dSetColorf(app.R2d, r / 255f, g / 255f, b / 255f, a / 255f);
            Bindings.ShapeDrawRectangle(app.R2d, "line", x, y, w, h);
        }

        public static void Line(GameApp app, float x1, float y1, float x2, float y2,
                                int r, int g, int b, int a = 255)
        {
            Bindings.R2dSetColorf(app.R2d, r / 255f, g / 255f, b / 255f, a / 255f);
            Bindings.ShapeDrawLine(app.R2d, x1, y1, x2, y2);
        }

        public static void Text(GameApp app, string text, float x, float y,
                                int r = 232, int g = 236, int b = 245)
        {
            if (app.Assets.FontSmall == null) return;
            Bindings.JtextPrintx(app.R2d, app.Assets.FontSmall, text,
                                 Encoding.UTF8.GetByteCount(text),
                                 (uint)r, (uint)g, (uint)b, 255u, x, y);
        }

        public static void TextCenter(GameApp app, string text, float cx, float cy, bool big = false,
                                      int r = 232, int g = 236, int b = 245)
        {
            Font font = big ? app.Assets.FontBig : app.Assets.FontSmall;
            if (font == null) return;

            int size = big ? 22 : 12;
            float w = TextWidthEstimate(text, size);
            Bindings.JtextPrintx(app.R2d, font, text,
                                 Encoding.UTF8.GetByteCount(text),
                                 (uint)r, (uint)g, (uint)b, 255u,
                                 cx - w * 0.5f, cy - size * 0.5f);
        }

        public static int TextWidth(GameApp app, string text)
        {
            if (app.Assets.FontSmall == null) return 0;
            return (int)TextWidthEstimate(text, 12);
        }

        private static float TextWidthEstimate(string text, int size)
        {
            float w = 0f;
            foreach (char c in text) w += c > 127 ? size : size * 0.58f;
            return w;
        }

        /// <summary>
        /// 以 (cx, cy) 为中心画精灵。ImageDrawRect 是全标量版图片绘制
        /// （srcrect 固定 NULL 表示整张图），绕开了 joy_rect_t* 无法进
        /// joy_value 的 L3 限制。图片缺失时退回同尺寸色块。
        /// </summary>
        public static void Sprite(GameApp app, Image image, float cx, float cy, float size,
                                  int fallbackR, int fallbackG, int fallbackB)
        {
            if (image != null)
            {
                Bindings.ImageDrawRect(app.R2d, image,
                                    cx - size * 0.5f, cy - size * 0.5f, size, size);
                return;
            }
            Fill(app, cx - size * 0.5f, cy - size * 0.5f, size, size,
                 fallbackR, fallbackG, fallbackB);
        }
    }
}
