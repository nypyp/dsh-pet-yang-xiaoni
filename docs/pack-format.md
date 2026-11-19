# DSH Go 宠物包格式摘要（schema 1）

本仓库只用到 schema 1 的一个子集。完整规格以 dsh-go 仓库的 `docs/design/pets.md` 为准，
官方校验器是 app 自带 `pet-theme` 技能里的 `pet_pack_check.py`。

## 目录 / zip

```
pack.json          # 必须在 zip 顶层（或唯一的单层文件夹里）
idle.png           # 序列帧图，扁平文件名，不能带路径
...
```

- 一个包 = 一个 `pack.json` + 若干 PNG；只保留清单里引用到的图。
- 限制：zip ≤ 64 MiB、条目 ≤ 256；单张 PNG ≤ 8 MiB 且任一边 ≤ 4096 px；解码后单张 ≤ 16 MiB。
- 市场规范化的 zip 要求确定性：`pack.json` 在前、PNG 按名字排序、固定时间戳、不带 PNG 元数据。

## pack.json 关键字段

| 字段 | 说明 | 本包取值 |
| --- | --- | --- |
| `schema` | 固定 `1` | `1` |
| `id` | 小写字母/数字/`-`，≤48 字符；导入后变成 `user-<id>` | `yang-xiaoni` |
| `name` | 展示名 | 阳小妮 |
| `author` / `license` / `source` | 宠物页底部原样显示，市场必填 | nypyp / CC BY-NC-SA 4.0 / 原创像素重绘 |
| `pixelArt` | 像素画为 `true`，按整数倍锐利绘制 | `true` |
| `scale` | 源图相对美术像素的倍率；1 表示源图就是美术像素 | `1` |
| `canvas` | 逻辑画布 | 56×72 |
| `anchor` | `x` 水平中心、`baseline` 脚线 | 28 / 66 |
| `contentBox` | 身体范围，决定 App 里的显示大小 | 14,22,35,48 |
| `animations` | 动画名 → 序列帧图、帧格 | 26 段 |

## animations 的一项

```json
"idle": {
  "sheet": "idle.png",
  "frameW": 35, "frameH": 48,
  "cols": 24,
  "box": {"x": 14, "y": 22, "w": 35, "h": 48},
  "loop": true,
  "ms": 100,
  "frames": [{"i": 0, "ms": 100}, {"i": 1, "ms": 100}]
}
```

- `frameW`/`frameH` 必须等于 `trunc(Float32(Float32(box.w/h) * scale))`，否则 App 导入门会拒绝。
- 一张图按行主序排 `cols` 列；PNG 尺寸要等于 `frameW × cols` 宽、`ceil((max i // cols)+1) × frameH` 高。
- `frames[].ms` 是每帧停留毫秒数（本包 50–100 ms/帧）。
- 帧图裁剪到这段动画实际有像素的范围，`box` 是贴回画布的位置。

## states / reactions / 其他

- `states`：Clawd 状态名 → 动画数组；`idle` 必须存在。本包覆盖 `idle / thinking / working / juggling / error / attention / notification / sweeping / carrying / sleeping / waking / roam`。
- `reactions`：`tapLeft`、`tapRight`、`tickle`、`annoyed`、`drag`。多动画用「基础名 + 编号」（`tickle2`、`tickle3`），**不要写数组**——旧版 App 只读基础名，数组会让整包被拒。
- `idlePool`：空闲时随机插播的小动画（间隔、权重、时长）。
- `bonus`：某个状态进入时按概率抽的彩蛋动画（本包 `attention` 35% 抽 `smile-hearts`）。
- `timings`：`minDisplay` / `autoReturn` / `wakeMs` 控制状态停留。
- `roam`：游走动画与朝向（正面美术写 `faces: "front"`）。
- `sleep`：空闲多久入睡。
- `hitBoxes`：命中区；不写时用 `contentBox`。

## 兼容性约定

- 未知字段会被忽略，导出时丢弃——可以加注释性字段，但别依赖它们。
- 缺 `states` 的状态播 `states.idle[0]`；缺 `reactions` 键则跳过该手势；不会因此整包被拒。
- `reactions` 的编号键只在基础名存在时合并；孤立编号保留为独立反应名。
