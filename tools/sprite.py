"""Pixel-art driver for the cat pet: parts + poses -> frames (art px, 1x)."""
import numpy as np

W, H = 56, 72
YOFF = 16   # headroom above the cat for thought clouds / hearts
PALETTE = {
    'outline':   (78, 66, 58),
    'fur':       (252, 249, 244),
    'shade':     (235, 228, 217),
    'deep':      (212, 200, 186),
    'patch':     (168, 166, 170),
    'patch_dk':  (131, 128, 135),
    'ear_in':    (243, 184, 187),
    'eye':       (57, 53, 51),
    'eye_hi':    (255, 255, 255),
    'nose':      (228, 152, 158),
    'mouth':     (146, 106, 101),
    'blush':     (246, 205, 202),
    'toy':       (223, 192, 143),
    'toy_dk':    (191, 150, 95),
    'toy_line':  (120, 92, 62),
    'shadow':    (40, 36, 42),
    'whisker':   (198, 188, 174),
    'tongue':    (231, 150, 152),
    'heart':     (232, 110, 132),
    'heart_lt':  (250, 172, 182),
    'spark':     (255, 247, 214),
    'spark_lt':  (255, 255, 255),
    'sweat':     (150, 196, 228),
    'dust':      (176, 168, 158),
    'cloud':     (241, 246, 252),
    'cloud_sh':  (204, 217, 236),
}
NAMES = list(PALETTE)
IDX = {n: i + 1 for i, n in enumerate(NAMES)}

class Canvas:
    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.a = np.zeros((h, w), np.uint8)
    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[int(y)][int(x)] = IDX[c]
    def px_raw(self, x, y, idx):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[int(y)][int(x)] = idx
    def hline(self, x0, x1, y, c):
        if x1 < x0: x0, x1 = x1, x0
        for x in range(int(x0), int(x1) + 1): self.px(x, y, c)
    def vline(self, x, y0, y1, c):
        if y1 < y0: y0, y1 = y1, y0
        for y in range(int(y0), int(y1) + 1): self.px(x, y, c)
    def rect(self, x0, y0, x1, y1, c):
        for y in range(int(y0), int(y1) + 1): self.hline(x0, x1, y, c)
    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / max(rx, .01)) ** 2 + ((y - cy) / max(ry, .01)) ** 2 <= 1.0:
                    self.px(x, y, c)
    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            for i in range(len(pts)):
                x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % len(pts)]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(round(xs[i]), round(xs[i + 1]), y, c)
    def outline(self, color='outline', skip=('shadow',)):
        skipidx = {0} | {IDX[s] for s in skip}
        src = self.a.copy()
        out = np.zeros_like(src)
        for y in range(self.h):
            for x in range(self.w):
                if src[y, x] in skipidx: continue
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and src[ny, nx] in skipidx:
                        out[ny, nx] = IDX[color]
        self.a = np.where(out > 0, out, self.a)

def sgn(v): return 1 if v > 0 else (-1 if v < 0 else 0)

def draw_cat(c: Canvas, *, body_dy=0, head_dy=0, head_dx=0, squash=0.0,
             eye='open', tail=0, mouth='smile', ears=0, blush=0, lift=0,
             toy_dy=0, toy_dx=0, tilt=0, front_paws=0):
    base = int(round(50 + body_dy - lift)) + YOFF
    # ---------- tail (behind body) ----------
    th = 0.15 + tail * 0.22
    for i in range(20):
        t = i / 19.0
        x = 39 + 7 * np.sin(1.25 * t + th) * (0.5 + 0.5 * t)
        y = base - 2 - 14 * t + 1.0 * np.cos(1.25 * t + th)
        for k in range(2):
            c.px(round(x) + k, round(y), 'fur')
            if t < .8: c.px(round(x) + k, round(y) + 1, 'shade')
    # ---------- body ----------
    sq = max(-1.0, min(1.0, squash))
    top = int(round(31 + sq * 2 + body_dy * 0.4 - lift)) + YOFF
    half_top = 8
    half_bot = 12 + int(round(-sq * 2))
    for y in range(top, base + 1):
        t = (y - top) / max(1, base - top)
        half = half_top + (half_bot - half_top) * t
        half += 1.6 * np.sin(np.pi * t)          # belly bulge
        c.hline(28 - half, 28 + half, y, 'fur')
    # body shading: 1px rim on the right + bottom, chest tuft
    for y in range(top, base + 1):
        t = (y - top) / max(1, base - top)
        half = half_top + (half_bot - half_top) * t + 1.6 * np.sin(np.pi * t)
        c.px(int(round(28 + half)) - 1, y, 'shade')
    c.hline(23, 33, base - 1, 'shade')
    c.px(27, top + 4, 'shade'); c.px(29, top + 4, 'shade'); c.px(28, top + 5, 'shade')
    # front paws
    py = int(base - 2 - front_paws)
    c.ellipse(22, py, 4, 2, 'fur')
    c.ellipse(34, py, 4, 2, 'fur')
    for px_ in (22, 34):
        c.hline(px_ - 3, px_ + 3, py + 2, 'deep')
        c.vline(px_, py + 1, py + 2, 'deep')
        c.px(px_ - 1, py + 2, 'deep'); c.px(px_ + 1, py + 2, 'deep')
        c.hline(px_ - 3, px_ + 3, py - 3, 'shade')
    # ---------- head ----------
    hx = int(round(28 + head_dx + tilt * 1.5))
    hy = int(round(20 + head_dy - lift)) + YOFF
    c.ellipse(hx, hy, 12, 11, 'fur')
    c.ellipse(hx - 9, hy + 4, 4, 3, 'fur')       # left cheek
    c.ellipse(hx + 9, hy + 4, 4, 3, 'fur')       # right cheek
    # ears
    c.poly([(hx - 11, hy - 5), (hx - 7, hy - 12 - ears), (hx - 2, hy - 8)], 'fur')
    c.poly([(hx + 2, hy - 8), (hx + 7, hy - 12 - ears), (hx + 11, hy - 5)], 'fur')
    c.poly([(hx - 9, hy - 6), (hx - 7, hy - 10 - ears), (hx - 4, hy - 8)], 'ear_in')
    c.poly([(hx + 4, hy - 8), (hx + 7, hy - 10 - ears), (hx + 9, hy - 6)], 'ear_in')
    # head patch (gray, between the ears, with a streak down the forehead)
    for (dx, dy) in [(-4, -9), (-3, -9), (-1, -9), (0, -9),
                     (-5, -8), (-4, -8), (-3, -8), (-2, -8), (-1, -8), (0, -8), (1, -8),
                     (-5, -7), (-4, -7), (-3, -7), (-2, -7), (-1, -7), (0, -7),
                     (-4, -6), (-3, -6), (-2, -6), (-1, -6),
                     (-3, -5), (-2, -5)]:
        c.px(hx + dx, hy + dy, 'patch')
    for (dx, dy) in [(-3, -9), (0, -8), (-2, -7), (-4, -7), (-1, -6)]:
        c.px(hx + dx, hy + dy, 'patch_dk')
    # ---------- face ----------
    ex_l, ex_r = hx - 5, hx + 5
    if eye == 'open':
        for ex in (ex_l, ex_r):
            c.rect(ex - 1, hy - 1, ex + 1, hy + 2, 'eye')
            c.px(ex - 1, hy - 1, 'eye_hi'); c.px(ex, hy - 1, 'eye_hi')
            c.px(ex - 1, hy, 'eye_hi')
            c.px(ex - 2, hy, 'shade'); c.px(ex + 2, hy + 1, 'shade')
    elif eye == 'blink':
        for ex in (ex_l, ex_r):
            c.hline(ex - 2, ex + 2, hy + 2, 'eye')
            c.px(ex - 2, hy + 1, 'eye'); c.px(ex + 2, hy + 1, 'eye')
    elif eye == 'happy':
        for ex in (ex_l, ex_r):
            c.px(ex - 2, hy + 2, 'eye'); c.px(ex - 1, hy + 1, 'eye')
            c.hline(ex, ex + 1, hy + 1, 'eye')
            c.px(ex + 2, hy + 2, 'eye')
    elif eye == 'closed':
        for ex in (ex_l, ex_r):
            c.hline(ex - 2, ex + 2, hy + 2, 'eye')
            c.px(ex - 2, hy + 1, 'eye'); c.px(ex + 2, hy + 1, 'eye')
            c.px(ex - 3, hy + 2, 'whisker')
    elif eye == 'angry':
        for ex, s in ((ex_l, -1), (ex_r, 1)):
            xs = range(-2, 3) if s < 0 else range(2, -3, -1)
            for i, dx in enumerate(xs):
                c.px(ex + dx, hy + i - 1, 'eye')
            c.px(ex + (2 if s < 0 else -2), hy + 1, 'eye')
    elif eye == 'sleep':
        for ex in (ex_l, ex_r):
            c.hline(ex - 2, ex + 2, hy + 2, 'mouth')
            c.px(ex - 2, hy + 1, 'mouth'); c.px(ex + 2, hy + 1, 'mouth')
    # nose + mouth
    c.px(hx - 1, hy + 4, 'nose'); c.px(hx, hy + 4, 'nose'); c.px(hx, hy + 5, 'nose')
    if mouth == 'smile':
        c.px(hx - 1, hy + 6, 'mouth'); c.px(hx, hy + 7, 'mouth'); c.px(hx + 1, hy + 6, 'mouth')
    elif mouth == 'open':
        c.hline(hx - 1, hx + 1, hy + 6, 'mouth')
        c.px(hx - 1, hy + 7, 'tongue'); c.px(hx, hy + 7, 'tongue'); c.px(hx + 1, hy + 7, 'tongue')
    elif mouth == 'flat':
        c.hline(hx - 1, hx + 1, hy + 6, 'mouth')
    # whiskers

    if blush:
        c.hline(hx - 9, hx - 7, hy + 5, 'blush'); c.hline(hx + 7, hx + 9, hy + 5, 'blush')
    # ---------- plush toy beside the right paw ----------
    tx, ty = int(42 + toy_dx), int(base - 3 + toy_dy)
    c.ellipse(tx, ty, 4, 4, 'toy')
    c.px(tx - 3, ty - 4, 'toy_dk'); c.px(tx + 3, ty - 4, 'toy_dk')
    c.hline(tx - 4, tx - 2, ty - 4, 'toy_dk'); c.hline(tx + 2, tx + 4, ty - 4, 'toy_dk')
    c.px(tx - 2, ty - 1, 'toy_line'); c.px(tx + 2, ty - 1, 'toy_line')
    c.hline(tx - 1, tx + 1, ty + 1, 'toy_line')
    c.px(tx - 1, ty - 1, 'toy_dk'); c.px(tx + 1, ty - 1, 'toy_dk')
    return base

PROPS = {
    # 5x4 heart
    'heart':  ["XX.XX", "XXXXX", ".XXX.", "..X.."],
    'heart_s': ["X.X", "XXX", ".X."],
    'spark':  [".X.", "XXX", ".X."],
    'excl':   ["X", "X", "X", "X", ".", "X"],
    'qm':     [".XX.", "X..X", "...X", "..X.", "..X.", "....", "..X."],
    'sweat':  [".X.", ".X.", "XXX", "XXX"],
    'note':   ["....X", "...XX", "..X.X", "..X..", "..X..", "XXX..", "XXX.."],
    'dust':   ["XX", "XX"],
}
def _rows_from_circles(w, h, circles):
    rows = []
    for y in range(h):
        row = ''
        for x in range(w):
            on = any((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r for cx, cy, r in circles)
            row += 'X' if on else '.'
        rows.append(row)
    return rows

PROPS['cloud'] = _rows_from_circles(18, 11, [(9.0, 6.0, 4.4), (4.2, 7.2, 2.9),
                                            (13.8, 7.2, 2.9), (6.4, 3.6, 2.9),
                                            (11.6, 3.6, 3.1)])
PROPS['puff'] = _rows_from_circles(3, 3, [(1.5, 1.5, 1.55)])
PROPS['puff2'] = _rows_from_circles(5, 5, [(2.5, 2.5, 2.45)])
PROPS['z3'] = ["XXX", ".X.", "XXX"]
PROPS['z4'] = ["XXXX", "..X.", ".X..", "XXXX"]
PROPS['z5'] = ["XXXXX", "...X.", "..X..", ".X...", "XXXXX"]

PROP_COLORS = {
    'heart': 'heart', 'heart_s': 'heart', 'spark': 'spark', 'excl': 'eye',
    'qm': 'eye', 'sweat': 'sweat', 'note': 'patch_dk', 'dust': 'dust',
    'cloud': 'cloud', 'puff': 'cloud', 'puff2': 'cloud',
    'z3': 'cloud', 'z4': 'cloud', 'z5': 'cloud',
}

def draw_prop(c, kind, x, y):
    rows = PROPS[kind]
    col = PROP_COLORS[kind]
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == 'X':
                c.px(x + dx, y + dy, col)
    if kind in ('heart', 'heart_s') and rows[0].count('X') > 1:
        c.px(x, y, 'heart_lt')
    if kind == 'spark':
        c.px(x + 1, y + 1, 'spark_lt')
    if kind == 'cloud':
        for col in range(len(rows[0])):
            for row in range(len(rows) - 1, -1, -1):
                if rows[row][col] == 'X':
                    if row >= len(rows) - 2:
                        c.px(x + col, y + row, 'cloud_sh')
                    break
        # thinking dots inside the cloud
        for dx in (7, 9, 11):
            c.px(x + dx, y + 5, 'cloud_sh'); c.px(x + dx, y + 6, 'patch_dk')

def render(pose):
    c = Canvas()
    zzz = pose.pop('zzz', 0)
    props = pose.pop('props', ())
    draw_cat(c, **pose)
    if zzz:
        hx = 28 + pose.get('head_dx', 0) + int(round(pose.get('tilt', 0) * 1.5))
        hy = int(round(20 + pose.get('head_dy', 0) - pose.get('lift', 0))) + YOFF
        marks = [('z3', hx + 12, hy - 11), ('z4', hx + 15, hy - 16), ('z5', hx + 18, hy - 22)]
        n = max(1, int(round(zzz * 3)))
        for kind, x, y in marks[:n]:
            draw_prop(c, kind, x, y)
    for (kind, x, y) in props:
        draw_prop(c, kind, int(round(x)), int(round(y)) + YOFF)
    lift = pose.get('lift', 0.0) + pose.get('body_dy', 0) * -0.5
    if lift < 8:
        w = max(4, int(round(8 - lift * 0.8)))
        for x in range(28 - w, 28 + w):
            c.px(x, 52 + YOFF, 'shadow')
        for x in range(28 - w + 2, 28 + w - 2):
            c.px(x, 51 + YOFF, 'shadow')
    c.outline()
    return c
