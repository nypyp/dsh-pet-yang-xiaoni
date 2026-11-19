#!/usr/bin/env python3
"""Generate the static GIF gallery (gallery.html) from pack/pack.json.

    python3 tools/gallery_html.py

The page is self-contained apart from screenshots/anim/*.gif, so it works when
opened locally or served by GitHub Pages.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = json.loads((ROOT / 'pack' / 'pack.json').read_text(encoding='utf-8'))
META = json.loads((ROOT / 'pack-meta.json').read_text(encoding='utf-8'))

GROUPS = [
    ('待机小剧场', '空闲时按 40–280 秒的随机间隔插播', [
        ('idle', '待机', '基础循环：呼吸 + 尾巴轻摆'),
        ('idle-blink', '眨眼', '随机眨眼'),
        ('idle-tail', '张望', '左右张望'),
        ('idle-heart', '冒爱心', '头顶飘一颗爱心'),
        ('idle-stretch', '伸懒腰', '伸个懒腰'),
        ('idle-groom', '洗脸', '舔爪、擦脸（猫式清洁）'),
        ('idle-knead', '踩奶', '两只前爪轮流按压'),
        ('idle-yawn', '打哈欠', '张大嘴、闭眼，然后收回'),
    ]),
    ('状态动画', '由 DSH 的状态机决定什么时候播放', [
        ('thinking', '思考', '等模型 / 推理 / 重试：云朵 + 泡泡上冒'),
        ('thinking2', '思考彩蛋 · 盯飞蛾', '进入思考状态时 25% 抽一次'),
        ('working', '干活 · 追红点', '工具运行 / 回复流式输出：盯梢、甩尾、扑抓'),
        ('working2', '干活彩蛋 · 毛线球', '进入干活状态时 20% 抽一次'),
        ('music', '多任务', '同时有多个会话在跑：跟着音符摇摆'),
        ('happy', '注意', '一整轮结束且 1.5 秒内没有新轮次'),
        ('smile-hearts', '注意彩蛋 · 爱心爆发', '进入注意状态时 35% 抽一次'),
        ('error', '出错', '一轮出错：炸毛 + 汗滴 + 感叹号'),
        ('notification', '通知', '有待确认 / 待回答的问题'),
        ('sweeping', '压缩', '压缩上下文时：压扁再弹回'),
        ('carrying', '搬运', '导入宠物包时'),
        ('sleeping', '睡觉', '90 秒无操作：闭眼 + Zzz'),
        ('waking', '唤醒', '睡觉时被碰一下'),
        ('roam-hop', '游走', '空闲时随机走动'),
    ]),
    ('手指互动', '需要你在 App 里真的去点 / 拖', [
        ('react-left', '点左边', '点身体左半边（与爱心版各 50%）'),
        ('react-left2', '点左边 · 爱心', '点身体左半边的爱心变体'),
        ('react-right', '点右边', '点身体右半边（与爱心版各 50%）'),
        ('react-right2', '点右边 · 爱心', '点身体右半边的爱心变体'),
        ('react-tickle', '挠痒 · 爱心', '1.1 秒内连点 3 下（三种随机之一）'),
        ('react-tickle2', '挠痒 · 星星', '1.5 秒内连点 3 下（三种随机之一）'),
        ('react-tickle3', '挠痒 · 害羞', '1.5 秒内连点 3 下（三种随机之一）'),
        ('react-annoyed', '恼了', '1.1 秒内连点 6 下（App 侧阈值）'),
        ('react-drag', '拖动', '按住拖动时'),
    ]),
]

CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.5 -apple-system, "Noto Sans CJK SC", "PingFang SC", system-ui, sans-serif;
       background: #14161b; color: #e8e4e2; }
a { color: #ffb3c1; }
header { padding: 26px 22px 18px; border-bottom: 1px solid #2a2e37;
         background: linear-gradient(180deg, #1b1e25, #14161b); }
h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: .5px; }
.sub { color: #9aa0ad; font-size: 13px; }
.sub b { color: #e8e4e2; font-weight: 600; }
.nav { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 8px; }
.nav a, .nav button { font: inherit; font-size: 13px; padding: 5px 11px; border-radius: 999px;
  border: 1px solid #343a46; background: #20242c; color: #d7d2d0; cursor: pointer; text-decoration: none; }
.nav a:hover, .nav button:hover { border-color: #5a6274; }
main { padding: 18px 22px 60px; max-width: 1180px; margin: 0 auto; }
section { margin: 26px 0 6px; }
h2 { font-size: 18px; margin: 0 0 4px; }
h2 .hint { font-size: 12px; color: #8b919d; font-weight: 400; margin-left: 8px; }
.grid { display: grid; gap: 14px; margin-top: 14px;
        grid-template-columns: repeat(auto-fill, minmax(178px, 1fr)); }
.card { background: #1b1e25; border: 1px solid #2a2f3a; border-radius: 12px; padding: 10px;
        display: flex; flex-direction: column; }
.card .shot { background: #202430; border-radius: 8px; display: flex; justify-content: center;
              padding: 6px 0; }
.card img { width: 150px; height: auto; image-rendering: pixelated; }
.card .name { margin-top: 8px; font-size: 13px; font-weight: 600; }
.card code { color: #ffb3c1; font-size: 11px; }
.card .trig { color: #9aa0ad; font-size: 12px; margin-top: 3px; flex: 1; }
.card .meta { margin-top: 7px; color: #6f7684; font-size: 11px; }
footer { color: #6f7684; font-size: 12px; padding: 0 22px 40px; max-width: 1180px; margin: 0 auto; }
.big img { width: 220px; }
body.fast img { animation: none; }
"""


def card(anim, label, trigger):
    a = PACK['animations'][anim]
    total = sum(f['ms'] for f in a['frames'])
    loop = '循环' if a['loop'] else '单次'
    gif = f'screenshots/anim/{anim}.gif'
    return f'''      <article class="card" data-anim="{anim}">
        <div class="shot"><img src="{gif}" alt="{label}" loading="lazy"></div>
        <div class="name">{label} <code>{anim}</code></div>
        <div class="trig">{trigger}</div>
        <div class="meta">{len(a['frames'])} 帧 · {total} ms · {loop}</div>
      </article>'''


def build():
    seen = set()
    sections = []
    for title, hint, items in GROUPS:
        cards = []
        for anim, label, trigger in items:
            if anim not in PACK['animations']:
                raise SystemExit(f'{anim} is not in the pack')
            seen.add(anim)
            cards.append(card(anim, label, trigger))
        sections.append(f'<section><h2>{title}<span class="hint">{hint}</span></h2>\n'
                        '    <div class="grid">\n' + '\n'.join(cards) + '\n    </div>\n  </section>')
    missing = set(PACK['animations']) - seen
    if missing:
        raise SystemExit(f'animations without a gallery card: {sorted(missing)}')
    body = '\n  '.join(sections)
    html = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{META["name"]} · 全部动效</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>{META["name"]} · 全部 {len(PACK["animations"])} 段动效</h1>
  <div class="sub"><b>DSH Go 像素宠物包</b> · {META["author"]} · {META["license"]} ·
    画布 {PACK["canvas"]["w"]}×{PACK["canvas"]["h"]} · 每格循环播放对应动画</div>
  <div class="nav">
    <a href="README.md">← 回到 README</a>
    <a href="screenshots/animations.png">总览图</a>
    <a href="dist/{META["id"]}.zip">下载宠物包</a>
    <button onclick="document.body.classList.toggle('big')">切换大小</button>
  </div>
</header>
<main>
  {body}
</main>
<footer>
  动画由 <code>tools/sprite.py</code> + <code>tools/build_pack.py</code> 生成，GIF 由
  <code>tools/gallery_html.py</code> 引用；触发条件见上方说明与 README。
  非官方作品，与 DSH Go 官方无关。
</footer>
</body>
</html>
'''
    (ROOT / 'gallery.html').write_text(html, encoding='utf-8')
    print(f'gallery.html ({len(PACK["animations"])} animations)')


if __name__ == '__main__':
    build()
