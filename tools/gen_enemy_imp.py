import zlib, struct, math

# ============================================================
# 敌人纹理生成器（与玩家贴图同一画风）—— 史莱姆
# 玩家画风实测：64x64 调色板 PNG；深墨 #2A2A2A 粗描边(约2px) + 白色内衬(约2px)
#             + 纯色主体块；剪影为圆角团。
# 史莱姆设计：同款三层结构；剪影 = 椭圆穹顶 + 平底（宽>高，经典史莱姆轮廓）；
#            脸 = 两只深色眼窝(带白高光点) + 锯齿嘴；主色用品红 #F04C9E
#            （与 绿/紫/红/黄 四个玩家色都不撞，且明显"敌方"）。
# ============================================================
W = H = 64
CX, CY = 32.0, 32.0

# 调色板（索引 → RGBA）
PAL = [
    (0,   0,   0,   0),      # 0 透明
    (42,  42,  42,  255),    # 1 深墨描边  #2A2A2A（与玩家一致）
    (255, 255, 255, 255),    # 2 白内衬
    (240, 76,  158, 255),    # 3 品红主体  #F04C9E
]
ID_INK, ID_WHITE, ID_CORE = 1, 2, 3

OUTLINE_W = 2.0   # 描边宽（像素）
PAD_W     = 2.0   # 白色内衬宽（像素）

# ---- 剪影：椭圆穹顶 + 平底（宽 42 x 高 30）----
RX, RY = 21.0, 20.0      # 椭圆半轴
BOTTOM  = 10.0           # 平底位置（局部 y，向下为正）

def ellipse_sdf(px, py):
    # 近似椭圆有符号距离（轴向上精确）
    return (math.sqrt((px / RX) ** 2 + (py / RY) ** 2) - 1.0) * min(RX, RY)

def silhouette(px, py):
    # 椭圆 与 半平面 py<=BOTTOM 的交集（取 max）
    return max(ellipse_sdf(px, py), py - BOTTOM)

# ---- 脸：深色眼窝(带白高光) + 锯齿嘴 ----
EYES    = [(-7.5, -6.0), (7.5, -6.0)]   # 眼窝中心
EYE_R   = 4.0                            # 眼窝半径
GLINT   = [(-9.5, -7.5), (9.5, -7.5)]   # 高光点中心
GLINT_R = 1.3

MOUTH_HW  = 8.0     # 嘴半宽
MOUTH_TOP = 0.5     # 嘴上沿基准
MOUTH_AMP = 1.8     # 锯齿起伏
MOUTH_BOT = 5.0     # 嘴下沿

def tri(t):
    """周期 1 的三角波，范围 0..1"""
    f = t - math.floor(t)
    return 2.0 * f if f < 0.5 else 2.0 * (1.0 - f)

def in_mouth(px, py):
    if abs(px) > MOUTH_HW:
        return False
    return (MOUTH_TOP + MOUTH_AMP * tri(px / 3.0)) <= py <= MOUTH_BOT

# ---- 光栅化：三层结构（描边 → 白内衬 → 主体），硬边对齐玩家的 crisp 风格 ----
idx = bytearray(W * H)
for y in range(H):
    for x in range(W):
        px = x + 0.5 - CX
        py = y + 0.5 - CY
        d = silhouette(px, py)
        i = 0
        if -OUTLINE_W <= d < 0.0:
            i = ID_INK
        elif -(OUTLINE_W + PAD_W) <= d < -OUTLINE_W:
            i = ID_WHITE
        elif d < -(OUTLINE_W + PAD_W):
            i = ID_CORE
            # 眼窝 → 深墨；高光点 → 白；嘴 → 深墨
            if any(math.hypot(px - ex, py - ey) <= EYE_R for ex, ey in EYES):
                i = ID_INK
                if any(math.hypot(px - gx, py - gy) <= GLINT_R for gx, gy in GLINT):
                    i = ID_WHITE
            elif in_mouth(px, py):
                i = ID_INK
        idx[y * W + x] = i

# ---- 写调色板 PNG（colortype 3, bitdepth 8，与玩家贴图同格式）----
raw = bytearray()
for y in range(H):
    raw.append(0)                            # filter: none
    raw += idx[y * W:(y + 1) * W]

def chunk(typ, d):
    return struct.pack('>I', len(d)) + typ + d + \
           struct.pack('>I', zlib.crc32(typ + d) & 0xffffffff)

plte = b''.join(bytes((r, g, b)) for (r, g, b, a) in PAL)
trns = bytes(a for (r, g, b, a) in PAL)
ihdr = struct.pack('>IIBBBBB', W, H, 8, 3, 0, 0, 0)
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'PLTE', plte) + \
      chunk(b'tRNS', trns) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + \
      chunk(b'IEND', b'')

out = r'E:\c++\joy\joy_topdown_template\assets\joy_topdown_template\sprites\enemies\imp.png'
open(out, 'wb').write(png)
print('wrote', out, len(png), 'bytes')

from collections import Counter
c = Counter(idx)
names = {0: 'transparent', 1: 'ink#2A2A2A', 2: 'white', 3: 'core#F04C9E'}
for k, n in c.most_common():
    print('  %-14s %d px' % (names[k], n))
