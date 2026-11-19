import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import build_pack  # noqa: E402
import sprite  # noqa: E402
import validate_pack as vp  # noqa: E402

META = json.loads((ROOT / 'pack-meta.json').read_text(encoding='utf-8'))
PACK_DIR = ROOT / 'pack'
ZIP = ROOT / 'dist' / f"{META['id']}.zip"


def load_pack():
    return json.loads((PACK_DIR / 'pack.json').read_text(encoding='utf-8'))


def test_pack_dir_passes_import_gate():
    problems, _ = vp.validate_dir(PACK_DIR, compat_reactions=True)
    assert not problems, problems


def test_zip_passes_import_gate_and_market_rules():
    problems, _ = vp.validate_zip(ZIP, compat_reactions=True, market=True)
    assert not problems, problems


def test_zip_layout_is_flat_and_complete():
    with zipfile.ZipFile(ZIP) as zf:
        names = zf.namelist()
        pack = json.loads(zf.read('pack.json'))
    assert names[0] == 'pack.json'
    sheets = sorted(a['sheet'] for a in pack['animations'].values())
    assert names[1:] == sheets
    assert len(names) == len(pack['animations']) + 1
    assert len(set(names)) == len(names)


def test_metadata_matches_pack_meta():
    pack = load_pack()
    for key in ('id', 'name', 'author', 'license', 'source'):
        assert pack[key] == META[key], key
    assert vp.ID_RE.match(pack['id'])


def test_geometry_matches_android_gate():
    pack = load_pack()
    scale = pack['scale']
    assert vp.is_num_int(scale) and scale >= 1
    for name, a in pack['animations'].items():
        box = a['box']
        expected_w = vp.trunc(vp.f32(vp.f32(box['w']) * scale))
        expected_h = vp.trunc(vp.f32(vp.f32(box['h']) * scale))
        assert a['frameW'] == expected_w, name
        assert a['frameH'] == expected_h, name
        assert a['frameW'] % scale == 0 and a['frameH'] % scale == 0, name


def test_states_and_reactions_reference_real_animations():
    pack = load_pack()
    known = set(pack['animations'])
    assert 'idle' in pack['states'] and pack['states']['idle']
    for state, anims in pack['states'].items():
        assert anims and set(anims) <= known, state
    for key, value in pack['reactions'].items():
        assert isinstance(value, str) and value in known, key
    assert pack['roam']['anim'] in known
    for item in pack['idlePool']['anims']:
        assert item['anim'] in known


def _components(mask):
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    sizes = []
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            stack, seen[y, x], n = [(y, x)], True, 0
            while stack:
                cy, cx = stack.pop()
                n += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            sizes.append(n)
    return sorted(sizes, reverse=True)


def test_head_and_body_stay_connected_on_every_frame():
    """Regression: rounding half-pixel offsets once opened a 1px row between
    head and body; the outline painted it dark and the head looked detached.
    Fur colours (not outline/shadow) must stay one connected blob per frame."""
    skip = {0, sprite.IDX['outline'], sprite.IDX['shadow']}
    for name, spec in build_pack.anims().items():
        for i, pose in enumerate(spec['poses']):
            pose = {k: v for k, v in pose.items() if k not in ('props', 'zzz')}
            canvas = sprite.render(dict(pose))
            mask = np.array([[v not in skip for v in row] for row in canvas.a])
            big = [size for size in _components(mask) if size > 40]
            assert len(big) == 1, f'{name} frame {i}: head and body are separated'


def test_rebuild_is_reproducible(tmp_path):
    a, b = tmp_path / 'a', tmp_path / 'b'
    build_pack.build(out_dir=a, zip_path=tmp_path / 'a.zip')
    build_pack.build(out_dir=b, zip_path=tmp_path / 'b.zip')
    names = sorted(p.name for p in a.iterdir())
    assert names == sorted(p.name for p in b.iterdir())
    for name in names:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
    assert (tmp_path / 'a.zip').read_bytes() == (tmp_path / 'b.zip').read_bytes()


def test_committed_pack_is_up_to_date(tmp_path):
    build_pack.build(out_dir=tmp_path / 'fresh', zip_path=tmp_path / 'fresh.zip')
    for path in sorted(PACK_DIR.iterdir()):
        fresh = tmp_path / 'fresh' / path.name
        assert fresh.is_file(), f'{path.name} is missing from a fresh build'
        assert path.read_bytes() == fresh.read_bytes(), (
            f'{path.name} is stale — run `make build` and commit the result')
    assert ZIP.read_bytes() == (tmp_path / 'fresh.zip').read_bytes(), (
        'dist zip is stale — run `make build`')


def test_validator_rejects_broken_geometry(tmp_path):
    broken = tmp_path / 'broken'
    broken.mkdir()
    for path in PACK_DIR.iterdir():
        (broken / path.name).write_bytes(path.read_bytes())
    pack = json.loads((broken / 'pack.json').read_text(encoding='utf-8'))
    pack['animations']['idle']['frameW'] += 1
    (broken / 'pack.json').write_text(json.dumps(pack), encoding='utf-8')
    problems, _ = vp.validate_dir(broken, compat_reactions=True)
    assert any(p.startswith('geometry') for p in problems), problems


def test_validator_rejects_missing_sheet(tmp_path):
    broken = tmp_path / 'broken'
    broken.mkdir()
    for path in PACK_DIR.iterdir():
        if path.name != 'idle.png':
            (broken / path.name).write_bytes(path.read_bytes())
    problems, _ = vp.validate_dir(broken, compat_reactions=True)
    assert any('idle.png' in p for p in problems), problems
