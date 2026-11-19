#!/usr/bin/env python3
"""Render every animation as its own GIF plus one labelled contact sheet.

    python3 tools/gallery.py

Outputs:
    screenshots/anim/<animation>.gif   one loop per animation (README gallery)
    screenshots/animations.png         one labelled tile per animation
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / 'pack'
OUT_DIR = ROOT / 'screenshots' / 'anim'
PACK = json.loads((PACK_DIR / 'pack.json').read_text(encoding='utf-8'))
W, H = PACK['canvas']['w'], PACK['canvas']['h']
BG = (27, 30, 36)
BAR = (74, 79, 92)


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


def compose(anim, idx, k):
    fr = frame_img(anim, idx).resize((W * k, H * k), Image.NEAREST)
    img = Image.new('RGBA', (W * k + 24, H * k + 30), BG)
    base = PACK['anchor']['baseline'] * k
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 14 + base + 2, W * k + 18, 14 + base + 9], 4, fill=BAR)
    img.alpha_composite(fr, (12, 14))
    return img.convert('RGB')


def gifs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, a in PACK['animations'].items():
        frames, durations = [], []
        for i in range(a['cols']):
            frames.append(compose(name, i, 3))
            durations.append(a['frames'][i]['ms'])
        if not a['loop']:
            frames.append(frames[-1].copy())
            durations.append(400)
        path = OUT_DIR / f'{name}.gif'
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=durations, loop=0, optimize=True)
        total += path.stat().st_size
    print(f'{len(PACK["animations"])} gifs -> {OUT_DIR} ({total / 1024:.0f} KiB)')


def sheet():
    names = list(PACK['animations'])
    k = 2
    tile_w, tile_h = W * k * 3 + 26, H * k + 44
    cols = 4
    rows = (len(names) + cols - 1) // cols
    img = Image.new('RGB', (cols * tile_w + 16, rows * tile_h + 60), (22, 24, 29))
    d = ImageDraw.Draw(img)
    d.text((16, 14), f'{PACK["name"]} · 全部 {len(names)} 段动画', font=font(30), fill=(245, 240, 242))
    d.text((16, 50), '每格取 3 个关键帧；动图与触发条件见 README', font=font(16), fill=(150, 156, 168))
    for i, name in enumerate(names):
        a = PACK['animations'][name]
        ox = 16 + (i % cols) * tile_w
        oy = 72 + (i // cols) * tile_h
        d.rounded_rectangle([ox, oy, ox + tile_w - 10, oy + tile_h - 12],
                            10, fill=(31, 34, 40), outline=(50, 54, 64))
        picks = [0, a['cols'] // 2, a['cols'] - 1]
        for j, idx in enumerate(picks):
            fr = frame_img(name, idx).resize((W * k, H * k), Image.NEAREST)
            bg = Image.new('RGBA', fr.size, (36, 39, 46, 255))
            bg.alpha_composite(fr)
            img.paste(bg.convert('RGB'), (ox + 8 + j * (W * k + 4), oy + 8))
        d.text((ox + 8, oy + H * k + 14), name, font=font(16), fill=(232, 214, 220))
        d.text((ox + 8, oy + H * k + 32),
               f'{a["cols"]} 帧 · {sum(f["ms"] for f in a["frames"])} ms · '
               f'{"循环" if a["loop"] else "单次"}', font=font(13), fill=(140, 146, 160))
    path = ROOT / 'screenshots' / 'animations.png'
    img.save(path)
    print(f'contact sheet -> {path} {img.size}')


if __name__ == '__main__':
    gifs()
    sheet()
