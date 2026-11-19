#!/usr/bin/env python3
"""Build the 阳小妮 pet pack (DSH Go schema 1) into ./pack and ./dist.

    python3 tools/build_pack.py [--out DIR] [--zip FILE]

Everything is generated from tools/sprite.py + pack-meta.json, so the build is
reproducible: PNG sheets carry no metadata and the zip uses fixed timestamps.
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sprite  # noqa: E402

META_PATH = ROOT / 'pack-meta.json'
DEFAULT_OUT = ROOT / 'pack'
DEFAULT_DIST = ROOT / 'dist'


def load_meta():
    return json.loads(META_PATH.read_text(encoding='utf-8'))


import math

import numpy as np
from PIL import Image

W, H = sprite.W, sprite.H
SCALE = 1
BASELINE = 50 + sprite.YOFF
PAL = [(0, 0, 0, 0)] + [tuple(c) + (255,) for c in sprite.PALETTE.values()]


def to_rgba(canvas):
    a = canvas.a
    out = np.zeros((*a.shape, 4), np.uint8)
    for i, color in enumerate(PAL):
        m = a == i
        if i == sprite.IDX['shadow']:
            out[m] = (30, 27, 33, 70)
        else:
            out[m] = color
    return out


def frames_of(spec):
    return [to_rgba(sprite.render(dict(pose))) for pose in spec['poses']]


TAU = math.tau

def _clamp(x, lo=0.0, hi=1.0): return max(lo, min(hi, x))
def _ease(x):
    x = _clamp(x); return x * x * (3 - 2 * x)

def anims():
    A = {}
    def add(name, n, ms, loop, fn):
        ts = [(i / (n - 1) if not loop else i / n) for i in range(n)]
        A[name] = dict(poses=[fn(t) for t in ts], ms=ms, loop=loop)

    def H(x, y): return ('heart', x, y)
    def h(x, y): return ('heart_s', x, y)
    def S(x, y): return ('spark', x, y)
    def E(x, y): return ('excl', x, y)
    def Q(x, y): return ('qm', x, y)
    def D(x, y): return ('sweat', x, y)
    def N(x, y): return ('note', x, y)
    def du(x, y): return ('dust', x, y)

    # ---------- idle ----------
    def f_idle(t):
        s = math.sin(TAU * t)
        return dict(lift=0.6 * s, tail=2.5 * math.sin(TAU * t + 0.8))
    add('idle', 24, 100, True, f_idle)

    def f_blink(t):
        return dict(eye='blink' if 0.25 < t < 0.62 else 'open')
    add('idle-blink', 8, 60, False, f_blink)

    def f_tail(t):
        return dict(tail=3 * math.sin(TAU * t),
                    head_dx=(1 if math.sin(TAU * t + 0.6) > 0.3 else 0),
                    lift=0.4 * math.sin(TAU * t))
    add('idle-tail', 20, 100, False, f_tail)

    def f_heart(t):
        props = []
        if t > 0.22:
            u = _ease(_clamp((t - 0.22) / 0.62))
            y = max(0.0, 16 - 16 * u)
            props = [H(41, y)] if y > 1 else [h(42, 0)]
        return dict(blush=1 if t > 0.12 else 0, tail=1.5 * math.sin(TAU * t), props=props)
    add('idle-heart', 24, 100, False, f_heart)

    def f_stretch(t):
        s = math.sin(math.pi * _clamp((t - 0.08) / 0.85))
        props = []
        if s > 0.75: props = [S(14, 8), S(40, 6)]
        eye = 'closed' if 0.2 < t < 0.62 else ('happy' if s > 0.4 else 'open')
        return dict(squash=-0.8 * s, lift=1.6 * s, eye=eye,
                    mouth='open' if s > 0.55 else 'smile', props=props)
    add('idle-stretch', 24, 100, False, f_stretch)

    # ---------- busy / mood states ----------
    def f_thinking(t):
        # Two beats per loop so a long "thinking" state does not look frozen:
        # cloud + rising puffs, then a look-up and a blink, then back.
        bob = 0.9 * math.sin(TAU * t)
        props = [('cloud', 33, -11 + bob)]
        for ph in (0.0, 0.5):
            u = (t + ph) % 1.0
            if u < 0.62:
                x = 31 + 6 * u + 1.2 * math.sin(math.pi * u)
                y = 10 - 12 * u
                props.append(('puff2' if u > 0.3 else 'puff', x, y))
        if t > 0.52:  # second beat: a sparkle pops out of the cloud
            props.append(('spark', 48, 2 + 2 * math.sin(TAU * t * 2)))
        eye = 'blink' if 0.82 < t < 0.88 else 'open'
        return dict(head_dx=(1.2 * math.sin(TAU * t) + (1.5 if 0.5 < t < 0.75 else 0)),
                    head_dy=-0.8 if 0.5 < t < 0.62 else 0.0,
                    mouth='flat', ears=-1, eye=eye,
                    tail=1.5 * math.sin(TAU * t + 0.4), props=props)
    add('thinking', 36, 100, True, f_thinking)

    def f_thinking2(t):
        # Bonus: "a-ha" - eyes closed, head tilted, the cloud on the left and a
        # light bulb switching on at the right (Deepy's thinking cloud, but an
        # idea instead of a second cloud).
        props = [('cloud', 7, 2), ('bulb', 38, 3)]
        if t > 0.35:
            props += [('spark', 33, 2), ('spark', 45, 7)]
        if t > 0.7:
            props += [('spark', 36, 10)]
        return dict(eye='closed' if t > 0.15 else 'open', head_dx=-1,
                    head_dy=(-1 if 0.3 < t < 0.85 else 0), ears=0,
                    mouth='open' if t > 0.2 else 'smile', props=props)
    add('thinking2', 24, 100, False, f_thinking2)

    def f_working(t):
        # Cat sits behind a little laptop: screen glowing, paws drumming on the
        # keyboard, code glyphs floating up from the screen (Deepy's "typing"
        # beat, adapted to the cat). Every cycle it glances up at the screen.
        beat = math.sin(TAU * 4 * t)
        paw_l = 1 if beat > 0 else 0
        paw_r = 1 - paw_l
        look = 0.58 < t < 0.74
        props = [('laptop', 17, 41),
                 ('paw_small', 21, 48 - paw_l), ('paw_small', 31, 48 - paw_r)]
        for kind, ph, x0 in (('glyph1', 0.0, 23), ('glyph2', 0.33, 30), ('glyph3', 0.66, 35)):
            u = (t + ph) % 1.0
            if u < 0.7:
                props.append((kind, x0, 38 - 7 * u))
        if look:
            props.append(('spark', 39, 35))
        return dict(head_dy=(0.0 if look else 1.2), head_dx=(1 if look else 0),
                    ears=(1 if look else 0), eye='open',
                    mouth='open' if look else 'smile',
                    tail=1.0 * math.sin(TAU * t), props=props)
    add('working', 32, 100, True, f_working)

    def f_working2(t):
        # Bonus: hard hat + a construction-style progress bar filling up
        # (Deepy's "building" beat).
        hd = -1 if 0.2 < t < 0.8 else 0
        fill = 2 + 12 * t
        props = [('helmet', 22, 4 + hd), ('bar', 44, 33, fill)]
        if fill > 12:
            props += [('spark', 40, 27), ('spark', 47, 31)]
        return dict(head_dy=hd, ears=1, eye='open',
                    mouth='open' if fill > 12 else 'smile',
                    tail=2.0 * math.sin(TAU * t), props=props)
    add('working2', 24, 80, False, f_working2)

    def f_music(t):
        props = []
        for ph, x0 in ((0.0, 12), (0.5, 40)):
            u = (t + ph) % 1.0
            if u < 0.85:
                y = max(0.0, 18 - 22 * u)
                props.append(N(x0 + 2 * math.sin(TAU * u), y))
        return dict(head_dx=1 if math.sin(TAU * t) > 0 else -1,
                    tail=2.5 * math.sin(TAU * t + 1), lift=0.4 * math.sin(TAU * t), props=props)
    add('music', 16, 100, True, f_music)

    def f_sleeping(t):
        s = math.sin(TAU * t)
        return dict(body_dy=2, head_dy=2, eye='sleep', mouth='flat', ears=-1, tail=0,
                    zzz=_clamp(0.35 + 0.65 * ((t * 2) % 1)))
    add('sleeping', 32, 100, True, f_sleeping)

    def f_waking(t):
        up = _ease(_clamp(t / 0.45))
        props = [S(14, 8), S(40, 6)] if t > 0.65 else []
        eye = 'sleep' if t < 0.28 else ('blink' if t < 0.5 else 'open')
        return dict(body_dy=2 * (1 - up), head_dy=2 * (1 - up), eye=eye,
                    squash=-0.35 * math.sin(math.pi * _clamp((t - 0.3) / 0.7)),
                    ears=1 if t > 0.45 else -1, mouth='open' if 0.3 < t < 0.7 else 'smile', props=props)
    add('waking', 15, 100, False, f_waking)

    def f_error(t):
        shake = 2 * math.sin(TAU * 2 * t)
        props = [E(38 + 1.2 * math.sin(TAU * t), 2 + 1.5 * _clamp(math.sin(TAU * t + 1)))]
        if t < 0.6:
            props.append(D(40 + shake * 0.6, 11 + 2 * math.sin(TAU * t)))
        return dict(head_dx=shake, eye='angry', mouth='flat', ears=-1,
                    tail=4 + 1.2 * math.sin(TAU * t), props=props)
    add('error', 24, 100, True, f_error)

    def f_notification(t):
        hop = abs(math.sin(math.pi * t))
        props = [E(38, max(0.0, 1 + 2 * (1 - hop)))]
        if hop > 0.55: props += [S(12, 10), S(43, 8)]
        return dict(lift=5 * hop, squash=-0.3 * hop, eye='happy', ears=1,
                    mouth='open' if hop > 0.5 else 'smile', tail=1.5 * math.sin(TAU * t), props=props)
    add('notification', 16, 100, True, f_notification)

    def f_sweeping(t):
        sq = 0.7 * math.sin(TAU * t)
        props = []
        if abs(sq) > 0.45:
            props = [du(11, 48), du(43, 48)]
        return dict(squash=sq, eye='blink' if 0.42 < t < 0.58 else 'open', props=props)
    add('sweeping', 28, 100, True, f_sweeping)

    def f_carrying(t):
        return dict(head_dx=1.5 * math.sin(TAU * t), tail=2 + 1.5 * math.sin(TAU * t + 0.5),
                    lift=0.4 * math.sin(TAU * t))
    add('carrying', 16, 100, True, f_carrying)

    def f_roam(t):
        hop = abs(math.sin(math.pi * t))
        props = [du(11, 50), du(43, 50)] if hop < 0.12 else []
        return dict(lift=5 * hop, squash=0.25 - 0.4 * hop, ears=1 if hop > 0.5 else 0,
                    tail=1.5 * math.sin(TAU * t), props=props)
    add('roam-hop', 24, 50, True, f_roam)

    def f_happy(t):
        hop = abs(math.sin(math.pi * 2 * t))
        props = []
        if hop > 0.55:
            props = [H(40, max(0.0, 12 - 8 * hop))]
            if hop > 0.8: props.append(S(12, 8))
        return dict(lift=4 * hop, squash=-0.2 * hop, eye='happy', blush=1, ears=1,
                    mouth='open' if hop > 0.55 else 'smile',
                    tail=2 * math.sin(TAU * t), props=props)
    add('happy', 26, 100, True, f_happy)

    def f_smile_hearts(t):
        props = []
        for i, (ph, x0) in enumerate(((0.0, 40), (0.33, 12), (0.66, 43))):
            u = (t + ph) % 1.0
            y = max(0.0, 14 - 14 * u)
            kind = H if i == 0 else h
            props.append(kind(x0, y))
            if u > 0.45: props.append(S(x0 - 2, y))
        return dict(eye='happy', blush=1, mouth='open', ears=1,
                    head_dx=1.2 * math.sin(TAU * t), props=props)
    add('smile-hearts', 16, 100, True, f_smile_hearts)

    # ---------- touch reactions ----------
    def tap_profile(t):
        """0 → 1 (lean in) → hold → 0, over the whole reaction."""
        if t < 0.12: return _ease(t / 0.12)
        if t < 0.62: return 1 + 0.06 * math.sin(TAU * (t - 0.12) * 1.5)
        return 1 - _ease((t - 0.62) / 0.38)

    def f_tap(t, side):
        a = tap_profile(t)
        props = []
        if 0.1 < t < 0.5:
            props.append(S(12 if side < 0 else 44, 22))
        if 0.3 < t < 0.95:
            u = _ease(_clamp((t - 0.3) / 0.6))
            props.append(h(31 + side * 12, max(0.0, 14 - 14 * u)))
        return dict(head_dx=side * 2 * a, lift=1.0 * a, blush=1 if t > 0.04 else 0,
                    tail=2 * math.sin(TAU * t) * a, props=props)
    def f_tap_left(t):  return f_tap(t, -1)
    def f_tap_right(t): return f_tap(t, +1)
    add('react-left', 40, 50, False, f_tap_left)
    add('react-right', 40, 50, False, f_tap_right)

    def f_tap2(t, side):
        a = tap_profile(t)
        props = []
        if 0.15 < t < 0.9:
            u = _ease(_clamp((t - 0.15) / 0.75))
            props.append(h(31 + side * 12, max(0.0, 16 - 15 * u)))
        if 0.05 < t < 0.4:
            props.append(S(31 + side * 16, 20))
        return dict(head_dx=side * 1.5 * a, lift=0.8 * a, eye='happy', blush=1,
                    tail=2 * math.sin(TAU * t) * a, props=props)
    add('react-left2', 30, 60, False, lambda t: f_tap2(t, -1))
    add('react-right2', 30, 60, False, lambda t: f_tap2(t, +1))

    def f_tickle(t):
        wig = 1.7 * math.sin(TAU * 2.5 * t) * (1 - 0.5 * _clamp((t - 0.7) / 0.3))
        props = []
        for t0, x0 in ((0.08, 41), (0.34, 12), (0.58, 43)):
            u = (t - t0) / 0.55
            if 0 <= u <= 1:
                props.append(H(x0, max(0.0, 16 - 16 * _ease(u))))
        if 0.2 < t < 0.75: props.append(S(14, 10))
        return dict(head_dx=wig, eye='happy', blush=1, mouth='open' if 0.15 < t < 0.85 else 'smile',
                    tail=3 * math.sin(TAU * 2 * t), props=props)
    add('react-tickle', 24, 70, False, f_tickle)

    def f_tickle2(t):
        props = []
        for i, (t0, x, y) in enumerate(((0.08, 14, 8), (0.22, 39, 6), (0.36, 12, 16),
                                        (0.5, 42, 12), (0.64, 16, 4))):
            if t0 <= t <= t0 + 0.3:
                props.append(S(x, y))
        wig = 1.5 * math.sin(TAU * 3 * t) * (1 - 0.5 * _clamp((t - 0.7) / 0.3))
        return dict(head_dx=wig, eye='happy', blush=1, mouth='open' if 0.2 < t < 0.8 else 'smile',
                    props=props)
    add('react-tickle2', 22, 70, False, f_tickle2)

    def f_tickle3(t):
        shake = 2.2 * math.sin(TAU * 2.5 * t) * (1 - 0.4 * _clamp((t - 0.75) / 0.25))
        props = []
        if t > 0.42:
            u = _ease(_clamp((t - 0.42) / 0.5))
            props = [h(44, max(0.0, 13 - 13 * u))]
        return dict(head_dx=shake, eye='happy', blush=1,
                    mouth='open' if 0.3 < t < 0.85 else 'smile', props=props)
    add('react-tickle3', 22, 70, False, f_tickle3)

    def f_annoyed(t):
        # 1.8 s: angry from the first frame (so even a brief slot reads),
        # a strong shake, steam above the ears, then a huffy hold.
        shake = 2.2 * math.sin(TAU * 3 * t) * (1 - _clamp((t - 0.55) / 0.45))
        props = [E(38, 1 + 2 * abs(math.sin(math.pi * t * 3)))]
        for ph, x0 in ((0.0, 17), (0.5, 40)):
            u = (t + ph) % 1.0
            if u < 0.75:
                props.append(('steam', x0, 18 - 16 * u))
        return dict(head_dx=shake, eye='angry', ears=-1,
                    mouth='open' if 0.1 < t < 0.35 else 'flat',
                    tail=4 * math.sin(TAU * 3 * t), props=props)
    add('react-annoyed', 30, 60, False, f_annoyed)

    def f_drag(t):
        return dict(lift=3, squash=-0.8, eye='open', mouth='open', ears=-1,
                    head_dx=1.4 * math.sin(TAU * t), tail=4 + 2 * math.sin(TAU * t))
    add('react-drag', 20, 60, True, f_drag)

    return A

def write_zip(zip_path: Path, pack_dir: Path, pack_json: Path) -> None:
    """Deterministic zip: pack.json first, then sorted sheets, fixed timestamps."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    names = ['pack.json'] + sorted(p.name for p in pack_dir.glob('*.png'))
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            src = pack_json if name == 'pack.json' else pack_dir / name
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, src.read_bytes())


def build(out_dir: Path | None = None, zip_path: Path | None = None, meta: dict | None = None):
    meta = meta or load_meta()
    out_dir = Path(out_dir or DEFAULT_OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob('*.png'):
        old.unlink()

    animations = {}
    idle_frames = None
    rows = []
    for name, spec in anims().items():
        fr = frames_of(spec)
        if name == 'idle':
            idle_frames = fr
        alphas = np.stack([f[:, :, 3] for f in fr])
        ys, xs = np.where(alphas.max(axis=0) > 0)
        box = dict(x=int(xs.min()), y=int(ys.min()),
                   w=int(xs.max()) - int(xs.min()) + 1,
                   h=int(ys.max()) - int(ys.min()) + 1)
        fw, fh = box['w'] * SCALE, box['h'] * SCALE
        n = len(fr)
        sheet = np.zeros((fh, fw * n, 4), np.uint8)
        for i, f in enumerate(fr):
            sheet[:, i * fw:(i + 1) * fw] = f[box['y']:box['y'] + box['h'],
                                                box['x']:box['x'] + box['w']]
        fn = f'{name}.png'
        Image.fromarray(sheet).save(out_dir / fn, optimize=True)
        animations[name] = dict(sheet=fn, frameW=fw, frameH=fh, cols=n, box=box,
                                loop=spec['loop'], ms=spec['ms'],
                                frames=[dict(i=i, ms=spec['ms']) for i in range(n)])
        rows.append((name, box, fw * n, fh, n))

    body = np.stack([f[:, :, 3] == 255 for f in idle_frames])
    ys, xs = np.where(body.max(axis=0))
    content_box = dict(x=int(xs.min()), y=int(ys.min()),
                       w=int(xs.max()) - int(xs.min()) + 1,
                       h=int(ys.max()) - int(ys.min()) + 1)

    pack = {
        'schema': 1,
        'id': meta['id'],
        'name': meta['name'],
        'author': meta['author'],
        'license': meta['license'],
        'source': meta['source'],
        'pixelArt': True,
        'scale': SCALE,
        'canvas': dict(w=W, h=H),
        'anchor': dict(x=28, baseline=BASELINE),
        'contentBox': content_box,
        'hitBoxes': {'default': content_box},
        'animations': animations,
        'idlePool': {'everyMs': dict(mean=95000, min=40000, max=280000),
                     'anims': [dict(anim='idle-blink', ms=480, weight=3),
                               dict(anim='idle-tail', ms=2000, weight=2),
                               dict(anim='idle-heart', ms=2400, weight=2),
                               dict(anim='idle-stretch', ms=2400, weight=2)]},
        'states': {'idle': ['idle'], 'thinking': ['thinking'], 'working': ['working'],
                   'juggling': ['music'], 'error': ['error'], 'attention': ['happy'],
                   'notification': ['notification'], 'sweeping': ['sweeping'],
                   'carrying': ['carrying'], 'sleeping': ['sleeping'],
                   'waking': ['waking'], 'roam': ['roam-hop']},
        'bonus': {'attention': dict(anims=['smile-hearts'], chance=0.35),
                   'thinking': dict(anims=['thinking2'], chance=0.25),
                   'working': dict(anims=['working2'], chance=0.2)},
        'timings': {'minDisplay': dict(attention=5200, error=4800, sweeping=5600,
                                       notification=3200, carrying=3200,
                                       working=1000, thinking=1000),
                    'autoReturn': dict(attention=5200, error=4800, sweeping=5000,
                                       carrying=3200),
                    'wakeMs': 1500},
        'reactions': {'tapLeft': 'react-left', 'tapLeft2': 'react-left2',
                      'tapRight': 'react-right', 'tapRight2': 'react-right2',
                      'tickle': 'react-tickle', 'tickle2': 'react-tickle2',
                      'tickle3': 'react-tickle3', 'annoyed': 'react-annoyed',
                      'drag': 'react-drag'},
        'roam': {'anim': 'roam-hop', 'faces': 'front'},
        'sleep': {'afterMs': 90000},
    }
    pack_json = out_dir / 'pack.json'
    pack_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n',
                         encoding='utf-8')

    zpath = Path(zip_path) if zip_path else DEFAULT_DIST / f"{meta['id']}.zip"
    write_zip(zpath, out_dir, pack_json)

    for name, box, sw, sh, n in rows:
        print(f'{name:16s} box={box} sheet={sw}x{sh} frames={n}')
    print(f'contentBox {content_box}')
    print(f'pack  -> {out_dir}')
    print(f'zip   -> {zpath} ({zpath.stat().st_size} bytes)')
    return pack


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    ap.add_argument('--zip', default=None)
    a = ap.parse_args(argv)
    build(a.out, a.zip)


if __name__ == '__main__':
    main()
