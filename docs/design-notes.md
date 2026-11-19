# 设计说明

## 造型

参考照片里那只白猫：白毛、头顶左侧一小块**灰色斑**、粉色耳内、大黑眼加高光、粉色小鼻子，
身旁一只**米色小狮子玩偶**，一条向上卷的尾巴。全部在 56×72 的画布上手绘，调色板 24 色左右。

## 画布与锚点

| 项 | 值 | 说明 |
| --- | --- | --- |
| canvas | 56×72 | 头顶多留 16 px，给思考云朵/爱心/星星 |
| contentBox | 14,22,35,48 | 身体实际范围，决定 App 里的显示大小 |
| anchor.baseline | 66 | 脚线，坐在活动条胶囊上 |
| scale / pixelArt | 1 / true | 源图就是美术像素；App 按整数倍放大（标准 k=2、大 k=3） |

App 里「标准」档 `k = round(30 × dpr ÷ contentBox.h)`，dpr 2.75 时 k=2；
大档 k=3；自定义最高 90 dp（约 k=5）。像素画按整数倍放大，边缘始终是硬像素。

## 动画怎么做

`sprite.py` 把猫拆成部件（尾巴、身体、前爪、头、耳朵、斑块、脸、玩偶），
`build_pack.py` 里的每个动画都是一个 `pose(t)` 函数，按 24~40 帧采样：

- 动作参数：`body_dy`、`head_dx/dy`、`lift`、`squash`、`tail`、`ears`、`front_paws`、`eye`、`mouth`
- 道具：`props` 里放 `heart / heart_s / spark / excl / qm / sweat / note / dust / cloud / puff / z3-z5`
- 时间统一按参考宠物的量级：点按 2.0 s（40 帧 × 50 ms）、挠痒 1.68 s、状态循环 2.4~3.2 s

### 时长基准（对照 dsh-go 自带的 Deepy 小鲸鱼 / 鲸娘）

| 动画 | 本包 | Deepy | 鲸娘 |
| --- | --- | --- | --- |
| 点左/点右 | 40f / 2000ms | 40f / 2000ms | 11f / 2110ms |
| 挠痒 | 24f / 1680ms | 48f / 2400ms | 14f / 1680ms |
| 恼了 | 15f / 900ms | — | — |
| 拖动 | 20f / 1200ms 循环 | 24f / 1200ms | 10f / 900ms |
| 待机 | 24f / 2400ms | 48f / 2400ms | 21f / 5280ms |
| 睡觉 | 32f / 3200ms | 64f / 3200ms | 6f / 1980ms |

## 状态映射

`idle / thinking / working / juggling(music) / error / attention(happy) / notification /
sweeping / carrying / sleeping / waking / roam(hop)`，外加 `idlePool` 的眨眼、张望、冒爱心、伸懒腰。

## 想改的话

| 想改 | 改哪里 |
| --- | --- |
| 斑块大小/颜色、脸、玩偶、尾巴 | `tools/sprite.py` 的 `draw_cat` 与 `PALETTE`，一格 = 一个美术像素 |
| 动作幅度、时长、道具出现时机 | `tools/build_pack.py` 的 `anims()`，`*_ms` 和 `*_frames` 都是明文 |
| 名字/作者/许可/来源 | `pack-meta.json` |
| 显示大小 | 改 `contentBox`（注意同步 `baseline`）或让用户调「大/自定义」 |
