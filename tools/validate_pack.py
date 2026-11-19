#!/usr/bin/env python3
"""Validate a DSH Go pet pack (schema 1) without the app.

    python3 tools/validate_pack.py pack [--zip dist/yang-xiaoni.zip]
                                        [--compat-reactions] [--market]

Checks the documented import gate: required fields, integer geometry,
frameW/frameH == trunc(Float32(box) * scale), sheet bounds and decoded size,
animation references, zip layout and section limits. `--compat-reactions`
additionally requires every reaction to be a plain animation name (numbers such
as `tickle2` / `tickle3` are allowed; arrays are not), so an older app that only
reads the base name can still open the pack. `--market` requires the metadata a
community/market submission needs.

This is our own implementation of the rules published in the dsh-go repo
(docs/design/pets.md, app/tool/pet-pack.rules.json). The authoritative checker,
`pet_pack_check.py`, ships with the app's `pet-theme` skill; fetch it with
tools/fetch-official-checker.sh and run `make check-official`.

Standard library only.
"""
import argparse
import json
import os
import re
import struct
import sys
import zipfile
from pathlib import Path

LIMITS = {
    'pack_json': 262_144,
    'sheet': 8_388_608,
    'sheets': 64,
    'total_sheet_bytes': 50_331_648,
    'sheet_side': 4096,
    'decoded_sheet': 16_777_216,
    'sheet_name': 120,
    'archive': 67_108_864,
    'archive_entries': 256,
}
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]{0,47}$')
STATES = ('idle', 'thinking', 'working', 'juggling', 'error', 'attention',
          'notification', 'sweeping', 'carrying', 'sleeping', 'waking', 'roam')
REACTION_KEYS = re.compile(r'^(.*?)(\d+)$')


def f32(v):
    return struct.unpack('<f', struct.pack('<f', float(v)))[0]


def trunc(v):
    return int(v) if v >= 0 else -int(-v)


def is_num_int(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and float(v).is_integer()


def is_rect(v):
    if not isinstance(v, dict):
        return None
    keys = ('x', 'y', 'w', 'h')
    if not all(isinstance(v.get(k), (int, float)) and not isinstance(v.get(k), bool) for k in keys):
        return None
    w, h = v['w'], v['h']
    if w <= 0 or h <= 0:
        return None
    return dict(x=int(v['x']), y=int(v['y']), w=int(w), h=int(h))


def png_size(data):
    """Returns (width, height) from an RGBA/any PNG, or None when it is not one."""
    if len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n':
        return None
    length = struct.unpack('>I', data[8:12])[0]
    if data[12:16] != b'IHDR' or length != 13:
        return None
    w, h, depth, color = struct.unpack('>IIBB', data[16:26])
    if w <= 0 or h <= 0 or depth not in (1, 2, 4, 8, 16) or color not in (0, 2, 3, 4, 6):
        return None
    if b'IDAT' not in data or not data.rstrip(b'\x00').endswith(b'IEND\xaeB`\x82'):
        return None
    return w, h


class ProblemList(list):
    def add(self, code, detail=''):
        self.append(f'{code}: {detail}' if detail else code)


def _json_int(v, lo, hi):
    return is_num_int(v) and lo <= int(v) <= hi


def validate_manifest(pack, sheets, compat_reactions=False, market=False, problems=None):
    """Validates a parsed pack.json. `sheets` maps sheet name -> PNG bytes."""
    p = problems if problems is not None else ProblemList()
    if pack.get('schema') != 1:
        p.add('schema', 'must be 1')
    pid = pack.get('id')
    if not isinstance(pid, str) or not pid:
        p.add('id', 'missing')
    elif market and not ID_RE.match(pid):
        p.add('id', f'{pid!r} must match ^[a-z0-9][a-z0-9-]{{0,47}}$')
    canvas = pack.get('canvas') if isinstance(pack.get('canvas'), dict) else {}
    if not (_json_int(canvas.get('w'), 1, 1 << 30) and _json_int(canvas.get('h'), 1, 1 << 30)):
        p.add('canvas', 'w/h must be whole numbers >= 1')
    scale = pack.get('scale', 1)
    if not _json_int(scale, 1, 4096):
        p.add('scale', 'must be a whole number in 1..4096')
        scale = 1
    scale = int(scale)
    if not pack.get('pixelArt') in (True, False) and 'pixelArt' in pack:
        p.add('pixelArt', 'must be a boolean')
    content = is_rect(pack.get('contentBox'))
    if content is None:
        p.add('contentBox', 'required rect x,y,w,h with w/h > 0')
    animations = pack.get('animations') if isinstance(pack.get('animations'), dict) else {}
    if not animations:
        p.add('animations', 'non-empty map required')
    sheet_total = 0
    sheet_count = 0
    for name, a in animations.items():
        if not isinstance(a, dict):
            p.add('animations', f'{name} must be an object')
            continue
        sheet = a.get('sheet')
        fw, fh, cols = a.get('frameW'), a.get('frameH'), a.get('cols')
        box = is_rect(a.get('box'))
        frames = a.get('frames')
        if not isinstance(sheet, str) or not sheet or '/' in sheet or '\\' in sheet or sheet.startswith('.'):
            p.add('animations', f'{name}.sheet must be a flat file name')
            continue
        if len(sheet) > LIMITS['sheet_name']:
            p.add('animations', f'{name}.sheet name too long')
        if not (_json_int(fw, 1, 4096) and _json_int(fh, 1, 4096) and _json_int(cols, 1, 4096)):
            p.add('animations', f'{name}: frameW/frameH/cols must be whole numbers in 1..4096')
            continue
        fw, fh, cols = int(fw), int(fh), int(cols)
        if box is None:
            p.add('animations', f'{name}.box must be a rect')
            continue
        if not isinstance(frames, list) or not frames:
            p.add('animations', f'{name}.frames must be a non-empty list')
            continue
        idxs = []
        for f in frames:
            if not isinstance(f, dict) or not _json_int(f.get('i'), 0, 1 << 30) or not _json_int(f.get('ms'), 1, 1 << 30):
                p.add('animations', f'{name}: every frame needs whole i >= 0 and ms >= 1')
                break
            idxs.append(int(f['i']))
        if fw != trunc(f32(f32(box['w']) * scale)) or fh != trunc(f32(f32(box['h']) * scale)):
            p.add('geometry', f'{name}: frameW/frameH != trunc(Float32(box) * scale)')
        if 'loop' in a and not isinstance(a['loop'], bool):
            p.add('animations', f'{name}.loop must be boolean')
        data = sheets.get(sheet)
        if data is None:
            p.add('sheets', f'{name}: missing {sheet}')
            continue
        sheet_count += 1
        sheet_total += len(data)
        if len(data) > LIMITS['sheet']:
            p.add('sheets', f'{name}: sheet larger than 8 MiB')
        size = png_size(data)
        if size is None:
            p.add('sheets', f'{name}: {sheet} is not a clean PNG')
            continue
        w, h = size
        if max(w, h) > LIMITS['sheet_side']:
            p.add('sheets', f'{name}: sheet side > 4096')
        if w * h * 4 > LIMITS['decoded_sheet']:
            p.add('sheets', f'{name}: decoded sheet > 16 MiB')
        rows = max(idxs) // cols + 1
        if w != fw * cols or h < rows * fh:
            p.add('sheets', f'{name}: {sheet} is {w}x{h}, expected {fw * cols}x{rows * fh}')
    if sheet_count > LIMITS['sheets']:
        p.add('sheets', 'more than 64 sheets')
    if sheet_total > LIMITS['total_sheet_bytes']:
        p.add('sheets', 'sheet bytes exceed 48 MiB')
    if market:
        for key in ('author', 'license', 'source'):
            v = pack.get(key)
            if not isinstance(v, str) or not v.strip():
                p.add('metadata', f'market submission needs a non-empty {key!r}')
    states = pack.get('states') if isinstance(pack.get('states'), dict) else {}
    if 'idle' not in [k for k, v in states.items() if isinstance(v, list) and v]:
        p.add('states', 'states.idle is required')
    known = set(animations)

    def ref(name, where):
        if not isinstance(name, str) or name not in known:
            p.add('references', f'{where} -> {name!r} is not an animation')

    for key, value in states.items():
        if not isinstance(value, list):
            continue
        for name in value:
            ref(name, f'states.{key}')
    tiers = pack.get('tiers') if isinstance(pack.get('tiers'), dict) else {}
    for key, value in tiers.items():
        if isinstance(value, list):
            for t in value:
                if isinstance(t, dict):
                    ref(t.get('anim'), f'tiers.{key}')
    reactions = pack.get('reactions') if isinstance(pack.get('reactions'), dict) else {}
    for key, value in reactions.items():
        items = value if isinstance(value, list) else [value]
        if compat_reactions and not isinstance(value, str):
            p.add('reactions', f'{key} must be a plain string for older apps')
        elif isinstance(value, list) and not value:
            p.add('reactions', f'{key} is an empty list')
        for name in items:
            ref(name, f'reactions.{key}')
    roam = pack.get('roam') if isinstance(pack.get('roam'), dict) else {}
    if 'anim' in roam:
        ref(roam.get('anim'), 'roam.anim')
    pool = pack.get('idlePool')
    pool_items = pool if isinstance(pool, list) else (
        (pool or {}).get('anims', []) if isinstance(pool, dict) else [])
    for item in pool_items:
        if isinstance(item, dict):
            ref(item.get('anim'), 'idlePool')
    bonus = pack.get('bonus') if isinstance(pack.get('bonus'), dict) else {}
    for key, value in bonus.items():
        if isinstance(value, dict):
            for name in value.get('anims', []) or []:
                ref(name, f'bonus.{key}')
    return p


def validate_zip(path, compat_reactions=False, market=False):
    p = ProblemList()
    raw = Path(path).read_bytes()
    if len(raw) > LIMITS['archive']:
        p.add('zip', 'archive larger than 64 MiB')
    try:
        zf = zipfile.ZipFile(path.__fspath__() if isinstance(path, Path) else path)
    except zipfile.BadZipFile as exc:
        p.add('zip', f'not a zip: {exc}')
        return p, {}
    infos = zf.infolist()
    if len(infos) > LIMITS['archive_entries']:
        p.add('zip', 'more than 256 entries')
    names = [i.filename for i in infos]
    if len({n.casefold() for n in names}) != len(names):
        p.add('zip', 'duplicate (case-insensitive) member names')
    for info in infos:
        n = info.filename
        if n.startswith('/') or '\\' in n or '..' in n.split('/') or info.is_dir():
            p.add('zip', f'unsafe member {n!r}')
        if info.flag_bits & 0x1:
            p.add('zip', f'encrypted member {n!r}')
    manifests = [i for i in infos if i.filename == 'pack.json' or
                 (i.filename.count('/') == 1 and i.filename.endswith('/pack.json'))]
    if len(manifests) != 1:
        p.add('zip', 'zip must contain exactly one pack.json (root or one top folder)')
        return p, {}
    manifest = manifests[0]
    prefix = manifest.filename[:-len('pack.json')]
    raw_json = zf.read(manifest)
    if len(raw_json) > LIMITS['pack_json']:
        p.add('zip', 'pack.json larger than 256 KiB')
    try:
        pack = json.loads(raw_json.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        p.add('zip', f'pack.json is not valid UTF-8 JSON: {exc}')
        return p, {}
    if not isinstance(pack, dict):
        p.add('zip', 'pack.json must be an object')
        return p, {}
    animations = pack.get('animations') if isinstance(pack.get('animations'), dict) else {}
    sheets = {}
    for a in animations.values():
        if isinstance(a, dict) and isinstance(a.get('sheet'), str):
            name = a['sheet']
            member = prefix + name
            if member in zf.namelist():
                sheets[name] = zf.read(member)
            else:
                p.add('sheets', f'{name} is referenced but missing from the zip')
    problems = validate_manifest(pack, sheets, compat_reactions, market)
    p.extend(problems)
    referenced = set(sheets) | {'pack.json'}
    extra = [n for n in names if n[len(prefix):] not in referenced and n != manifest.filename]
    if extra:
        p.add('zip', f'unreferenced members: {sorted(extra)[:5]}')
    return p, pack


def validate_dir(path, compat_reactions=False, market=False):
    root = Path(path)
    p = ProblemList()
    pack_file = root / 'pack.json'
    if not pack_file.is_file():
        p.add('dir', f'{pack_file} not found')
        return p, {}
    raw = pack_file.read_bytes()
    if len(raw) > LIMITS['pack_json']:
        p.add('dir', 'pack.json larger than 256 KiB')
    try:
        pack = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        p.add('dir', f'pack.json is not valid UTF-8 JSON: {exc}')
        return p, {}
    if not isinstance(pack, dict):
        p.add('dir', 'pack.json must be an object')
        return p, {}
    animations = pack.get('animations') if isinstance(pack.get('animations'), dict) else {}
    sheets = {}
    for a in animations.values():
        if isinstance(a, dict) and isinstance(a.get('sheet'), str):
            name = a['sheet']
            f = root / name
            if f.is_file():
                sheets[name] = f.read_bytes()
            else:
                p.add('sheets', f'{name} is referenced but missing')
    p.extend(validate_manifest(pack, sheets, compat_reactions, market))
    return p, pack


def main(argv=None):
    ap = argparse.ArgumentParser(description='Validate a DSH Go pet pack.')
    ap.add_argument('pack', help='pack directory (with pack.json) or a .zip')
    ap.add_argument('--zip', default=None, help='also validate this zip')
    ap.add_argument('--compat-reactions', action='store_true')
    ap.add_argument('--market', action='store_true')
    a = ap.parse_args(argv)
    targets = [a.pack] + ([a.zip] if a.zip else [])
    failed = False
    for target in targets:
        is_zip = str(target).lower().endswith('.zip')
        problems, _ = (validate_zip(target, a.compat_reactions, a.market) if is_zip
                       else validate_dir(target, a.compat_reactions, a.market))
        if problems:
            failed = True
            print(f'FAIL {target}')
            for problem in problems:
                print(f'  - {problem}')
        else:
            print(f'PASS {target}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
