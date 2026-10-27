import zlib, struct, math, os, sys

# ============================================================
# 敌人生成器（与玩家贴图同一画风）
# 玩家画风实测：64x64 调色板 PNG；深墨 #2A2A2A 粗描边(约2px) + 白色内衬(约2px)
#             + 纯色主体块；剪影为圆角团。
# 本脚本一次生成 6 种敌人，每种 = 同款三层结构 + 专属剪影/五官 + 独立主色。
# 主色刻意避开玩家四色(绿/紫/红/黄)并互相区分。
# ============================================================
W = H = 64
CX, CY = 32.0, 32.0

TRANS = (0, 0, 0, 0)
INK   = (42, 42, 42, 255)      # 深墨描边/五官  #2A2A2A（与玩家一致）
WHITE = (255, 255, 255, 255)

OUTLINE_W = 2.0   # 描边宽（像素）
PAD_W     = 2.0   # 白色内衬宽（像素）

ID_INK, ID_WHITE = 1, 2

# ---------------- SDF 基元 ----------------
def circle_sdf(px, py, cx, cy, r):
    return math.hypot(px - cx, py - cy) - r

def ellipse_sdf(px, py, cx, cy, rx, ry):
    return (math.hypot((px - cx) / rx, (py - cy) / ry) - 1.0) * min(rx, ry)

def rbox_sdf(px, py, cx, cy, hw, hh, rad):
    qx = abs(px - cx) - (hw - rad)
    qy = abs(py - cy) - (hh - rad)
    ox, oy = max(qx, 0.0), max(qy, 0.0)
    return math.sqrt(ox * ox + oy * oy) + min(max(qx, qy), 0.0) - rad

def seg_sdf(px, py, ax, ay, bx, by, r):
    ex, ey = bx - ax, by - ay
    L2 = ex * ex + ey * ey
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * ex + (py - ay) * ey) / L2))
    return math.hypot(px - (ax + t * ex), py - (ay + t * ey)) - r

def poly_sdf(px, py, v):
    """凸多边形有符号距离（内部为负）"""
    cx = sum(p[0] for p in v) / len(v)
    cy = sum(p[1] for p in v) / len(v)
    best = -1e18
    for i in range(len(v)):
        x1, y1 = v[i]
        x2, y2 = v[(i + 1) % len(v)]
        ex, ey = x2 - x1, y2 - y1
        L = math.hypot(ex, ey)
        if L == 0:
            continue
        nx, ny = ey / L, -ex / L
        d = nx * (px - x1) + ny * (py - y1)
        if nx * (cx - x1) + ny * (cy - y1) > 0.0:   # 法线朝内才翻转（内部转负）
            d = -d
        if d > best:
            best = d
    return best

def tri_wave(t):
    f = t - math.floor(t)
    return 2.0 * f if f < 0.5 else 2.0 * (1.0 - f)

# ---------------- 栅格化 ----------------
# 调色板索引：0 透明 / 1 深墨(描边+五官) / 2 白内衬 / 3 主体色
ID_CORE = 3

def raster(sil_fn, face_fn, core_rgb):
    idx = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            px = x + 0.5 - CX
            py = y + 0.5 - CY
            d = sil_fn(px, py)
            if -OUTLINE_W <= d < 0.0:
                i = ID_INK                  # 描边
            elif -(OUTLINE_W + PAD_W) <= d < -OUTLINE_W:
                i = ID_WHITE                # 白内衬
            elif d < -(OUTLINE_W + PAD_W):
                i = ID_CORE                 # 主体
            else:
                i = 0                       # 透明
            idx[y * W + x] = i
    # 第二遍：五官只在主体区覆盖（避免画到描边/白框上）
    for y in range(H):
        for x in range(W):
            if idx[y * W + x] != ID_CORE:
                continue
            px = x + 0.5 - CX
            py = y + 0.5 - CY
            f = face_fn(px, py)
            if f:
                idx[y * W + x] = f
    return idx

def write_png(path, idx, core_rgb):
    # 调色板：0 透明 / 1 深墨 / 2 白 / 3 主体色
    pal = [TRANS, INK, WHITE, core_rgb + (255,)]
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += idx[y * W:(y + 1) * W]
    def chunk(typ, d):
        return struct.pack('>I', len(d)) + typ + d + \
               struct.pack('>I', zlib.crc32(typ + d) & 0xffffffff)
    plte = b''.join(bytes(c[:3]) for c in pal)
    trns = bytes(c[3] for c in pal)
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 3, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'PLTE', plte) + \
          chunk(b'tRNS', trns) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + \
          chunk(b'IEND', b'')
    open(path, 'wb').write(png)
    return len(png)

def view(name, idx):
    print('\n==== %s ====' % name)
    print('     ' + ''.join(str(x % 10) for x in range(W)))
    for y in range(H):
        s = ''
        for x in range(W):
            i = idx[y * W + x]
            s += ' ' if i == 0 else ('#' if i == 1 else ('.' if i == 2 else 'G'))
        print('%3d  ' % y + s)

# ============================================================
# 1) 史莱姆 slime（沿用现有 imp.png 的造型）
# ============================================================
def slime():
    sil = lambda px, py: max(ellipse_sdf(px, py, 0, 0, 21, 20), py - 10.0)
    def face(px, py):
        if math.hypot(px + 7.5, py + 6.0) <= 4.0 or math.hypot(px - 7.5, py + 6.0) <= 4.0:
            if math.hypot(px + 9.5, py + 7.5) <= 1.3 or math.hypot(px - 9.5, py + 7.5) <= 1.3:
                return ID_WHITE
            return ID_INK
        if abs(px) <= 8.0 and (0.5 + 1.8 * tri_wave(px / 3.0)) <= py <= 5.0:
            return ID_INK
        return 0
    return sil, face, (240, 76, 158)          # 品红

# ============================================================
# 2) 蝙蝠 bat：窄身 + 双大三角翼 + 双尖耳
# ============================================================
def bat():
    def sil(px, py):
        return min(ellipse_sdf(px, py, 0, 0, 7, 9),
                   poly_sdf(px, py, [(-6, -6), (-27, -2), (-6, 7)]),
                   poly_sdf(px, py, [(6, -6), (27, -2), (6, 7)]),
                   poly_sdf(px, py, [(-5, -8), (-8, -16), (-2, -9)]),
                   poly_sdf(px, py, [(5, -8), (8, -16), (2, -9)]))
    def face(px, py):
        if math.hypot(px + 2.6, py + 1.0) <= 1.9 or math.hypot(px - 2.6, py + 1.0) <= 1.9:
            return ID_INK
        # 翼骨：两条浅色棱线（用白，体现"内衬"层次）
        if abs(seg_sdf(px, py, -5, -3, -20, -2, 0.9)) < 0.9 and px < -6:
            return ID_WHITE
        if abs(seg_sdf(px, py, 5, -3, 20, -2, 0.9)) < 0.9 and px > 6:
            return ID_WHITE
        return 0
    return sil, face, (62, 143, 224)           # 蓝

# ============================================================
# 3) 骷髅兵 skeleton：颅 + 颌，深色眼窝/鼻/牙
# ============================================================
def skeleton():
    def sil(px, py):
        return min(circle_sdf(px, py, 0, -5, 13),
                   rbox_sdf(px, py, 0, 7, 9, 6, 4))
    def face(px, py):
        # 眼窝
        if math.hypot(px + 5.5, py + 7.0) <= 3.4 or math.hypot(px - 5.5, py + 7.0) <= 3.4:
            return ID_INK
        # 鼻三角
        if poly_sdf(px, py, [(-2.0, 0.0), (2.0, 0.0), (0.0, 3.5)]) <= 0:
            return ID_INK
        # 牙床：深色带 + 每 3px 一道白缝 → 牙齿
        if abs(px) <= 7.0 and 4.0 <= py <= 7.0:
            if int(abs(px) * 10) % 30 < 12:
                return ID_WHITE
            return ID_INK
        return 0
    return sil, face, (237, 230, 216)          # 骨白

# ============================================================
# 4) 兽人 brute：宽肩窄腰 + 双角 + 獠牙
# ============================================================
def brute():
    def sil(px, py):
        return min(poly_sdf(px, py, [(-14, -12), (14, -12), (9, 14), (-9, 14)]),
                   poly_sdf(px, py, [(-12, -12), (-18, -20), (-4, -12)]),
                   poly_sdf(px, py, [(12, -12), (18, -20), (4, -12)]))
    def face(px, py):
        # 斜怒眉：两道短斜带（比整条实带利落，且不会糊成"面罩"）
        if seg_sdf(px, py, -11.0, -5.5, -3.0, -4.0, 1.1) <= 0.1:
            return ID_INK
        if seg_sdf(px, py, 11.0, -5.5, 3.0, -4.0, 1.1) <= 0.1:
            return ID_INK
        # 眼
        if math.hypot(px + 6.0, py + 1.0) <= 2.6 or math.hypot(px - 6.0, py + 1.0) <= 2.6:
            return ID_INK
        # 嘴
        if abs(px) <= 6.0 and 5.0 <= py <= 7.0:
            return ID_INK
        # 獠牙：白色梯形，自嘴沿向上翘（比三角形面积大、更显眼）
        if poly_sdf(px, py, [(-8.0, 5.0), (-4.0, 5.0), (-5.2, 0.5), (-6.8, 0.5)]) <= 0:
            return ID_WHITE
        if poly_sdf(px, py, [(8.0, 5.0), (4.0, 5.0), (5.2, 0.5), (6.8, 0.5)]) <= 0:
            return ID_WHITE
        return 0
    return sil, face, (232, 134, 46)           # 橙

# ============================================================
# 5) 邪法师 cultist：尖帽 + 帽檐 + 上窄下宽袍，兜影内两点亮眼
# ============================================================
def cultist():
    def sil(px, py):
        return min(poly_sdf(px, py, [(-7, -6), (7, -6), (17, 14), (-17, 14)]),
                   poly_sdf(px, py, [(-9, -5), (9, -5), (0, -26)]),
                   rbox_sdf(px, py, 0, -6, 12, 1.5, 1.0))
    def face(px, py):
        # 兜帽阴影：深色脸。位置必须落在"主体芯区"（描边+白内衬共 4px 之内不显示五官），
        # 袍顶在 py=-6，故芯区约 py>-2，兜影中心放到 py=2。
        if ellipse_sdf(px, py, 0, 2.0, 8.0, 5.0) <= 0:
            if math.hypot(px + 3.2, py - 1.0) <= 1.4 or math.hypot(px - 3.2, py - 1.0) <= 1.4:
                return ID_WHITE                 # 亮眼
            return ID_INK
        return 0
    return sil, face, (47, 182, 168)            # 青

# ============================================================
# 6) 蜘蛛 crawler：扁平椭圆身 + 每侧 3 条折腿
# ============================================================
def spider():
    def sil(px, py):
        return min(ellipse_sdf(px, py, 0, 0, 16, 11),
                   seg_sdf(px, py, -11, -4, -25, -13, 1.8),
                   seg_sdf(px, py, -15, 0, -29, 2, 1.8),
                   seg_sdf(px, py, -11, 4, -25, 13, 1.8),
                   seg_sdf(px, py, 11, -4, 25, -13, 1.8),
                   seg_sdf(px, py, 15, 0, 29, 2, 1.8),
                   seg_sdf(px, py, 11, 4, 25, 13, 1.8))
    def face(px, py):
        # 前排四只小眼（下移到主体芯区：ry=11 时芯区约 py>-7）
        for ex in (-7.0, -2.5, 2.5, 7.0):
            if math.hypot(px - ex, py + 5.0) <= 1.2:
                return ID_INK
        # 背甲棱线（白）
        if abs(py - 2.0) <= 0.9 and abs(px) <= 11.0:
            return ID_WHITE
        return 0
    return sil, face, (150, 116, 66)            # 褐

# ============================================================
ENEMIES = [
    ('imp.png',      '史莱姆 slime',  slime),
    ('bat.png',      '蝙蝠 bat',      bat),
    ('skeleton.png', '骷髅 skeleton', skeleton),
    ('brute.png',    '兽人 brute',    brute),
    ('cultist.png',  '邪法师 cultist', cultist),
    ('spider.png',   '蜘蛛 spider',   spider),
]

OUT = r'E:\c++\joy\joy_topdown_template\assets\joy_topdown_template\sprites\enemies'
os.makedirs(OUT, exist_ok=True)

show = '--view' in sys.argv
for fname, cname, fn in ENEMIES:
    sil, face, core = fn()
    idx = raster(sil, face, core)
    n = write_png(os.path.join(OUT, fname), idx, core)
    print('%-14s %-16s %4d bytes  core=#%02X%02X%02X' %
          (fname, cname, n, core[0], core[1], core[2]))
    if show:
        view(fname, idx)
