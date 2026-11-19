#!/usr/bin/env python3
"""Render screenshots/preview.png (state collage) and screenshots/preview.gif."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / 'pack'
SHOTS = ROOT / 'screenshots'
PACK = json.loads((PACK_DIR / 'pack.json').read_text(encoding='utf-8'))
W, H = PACK['canvas']['w'], PACK['canvas']['h']


def frame_img(anim, idx):
    a = PACK['animations'][anim]
    sheet = Image.open(PACK_DIR / a['sheet']).convert('RGBA')
    fw, fh = a['frameW'], a['frameH']
    cell = sheet.crop((idx * fw, 0, (idx + 1) * fw, fh))
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    c.alpha_composite(cell, (a['box']['x'], a['box']['y']))
    return c


def font(sz):
    for path in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                 '/System/Library/Fonts/PingFang.ttc'):
        try:
            return ImageFont.truetype(path, sz, index=2)
        except Exception:
            continue
    return ImageFont.load_default()


def collage():
    k = 6  # 3x the app's k=2 at the standard size
    items = [('idle', 0, '待机'), ('happy', 8, '注意 · 爱心'),
             ('react-tickle', 20, '挠痒 · 爱心'), ('react-tickle2', 10, '挠痒 · 星星'),
             ('thinking', 0, '思考 · 云朵'), ('sleeping', 4, '睡觉 · Zzz')]
    cellw, cellh = W * k + 30, H * k + 72
    cols, rows = 3, 2
    img = Image.new('RGBA', (cellw * cols + 28, cellh * rows + 128), (17, 19, 23, 255))
    d = ImageDraw.Draw(img)
    d.text((22, 18), f"{PACK['name']} · DSH Go 像素宠物", font=font(34), fill=(247, 242, 244))
    d.text((24, 66), '爱心 · 星星 · 思考云朵 · 感叹号 · 汗滴 · 音符 · Zzz　官方校验 PASS',
           font=font(17), fill=(150, 156, 168))
    for i, (anim, idx, label) in enumerate(items):
        fr = frame_img(anim, idx).resize((W * k, H * k), Image.NEAREST)
        ox = 22 + (i % cols) * cellw
        oy = 112 + (i // cols) * cellh
        d.rounded_rectangle([ox - 8, oy - 8, ox + cellw - 22, oy + cellh - 46],
                            14, fill=(27, 30, 36, 255), outline=(45, 49, 59, 255))
        base = PACK['anchor']['baseline'] * k
        d.rounded_rectangle([ox + 2, oy + base + 2, ox + W * k - 6, oy + base + 9],
                            4, fill=(74, 79, 92, 255))
        img.alpha_composite(fr, (ox, oy))
        d.text((ox + 2, oy + H * k + 2), label, font=font(20), fill=(230, 212, 218))
    img.convert('RGB').save(SHOTS / 'preview.png')
    print('screenshots/preview.png', img.size)


def gif():
    seq = [('idle', range(24)), ('idle-heart', range(24)), ('happy', range(26)),
           ('react-left', range(40)), ('react-tickle', range(24)), ('sleeping', range(16))]
    k = 3
    frames, durations = [], []
    for anim, idxs in seq:
        for idx in idxs:
            fr = frame_img(anim, idx).resize((W * k, H * k), Image.NEAREST)
            bg = Image.new('RGBA', (W * k + 30, H * k + 34), (17, 19, 23, 255))
            base = PACK['anchor']['baseline'] * k
            d = ImageDraw.Draw(bg)
            d.rounded_rectangle([8, 16 + base + 2, W * k + 22, 16 + base + 9],
                                4, fill=(74, 79, 92, 255))
            bg.alpha_composite(fr, (15, 16))
            frames.append(bg.convert('RGB'))
            durations.append(PACK['animations'][anim]['ms'])
    frames[0].save(SHOTS / 'preview.gif', save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True)
    print('screenshots/preview.gif', frames[0].size, len(frames), 'frames')


if __name__ == '__main__':
    SHOTS.mkdir(exist_ok=True)
    collage()
    gif()
