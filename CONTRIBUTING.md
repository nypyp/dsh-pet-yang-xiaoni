# 贡献指南

欢迎修 bug、调动画、加道具。改动前先读 [`docs/design-notes.md`](docs/design-notes.md) 和
[`docs/publishing.md`](docs/publishing.md)。

## 环境

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
```

需要 Python ≥ 3.10、Pillow、numpy；chromium 之类不需要。

## 常用命令

```sh
make build          # 重新生成 pack/ 和 dist/<id>.zip
make check          # 自研校验（导入门 + 市场元数据）
make check-official # 官方 checker（pinned commit，需要网络）
make test           # pytest
make preview        # 重新生成 screenshots/
```

## 提交前检查

- [ ] `make build && make check && make test` 全绿
- [ ] 如果改了动画/造型，`make preview` 更新截图，并在 PR 里贴一张对比图
- [ ] 如果改了 `pack-meta.json` 或包行为，更新 `CHANGELOG.md`
- [ ] 包 id 保持稳定；要换 id 请在 PR 里说明原因
- [ ] 不引入第三方美术素材；新道具自己画
- [ ] 提交信息用祈使句，例如 `feat: add tail-wag reaction`

## 代码风格

- Python 标准库优先；绘制/图像处理才用 Pillow、numpy。
- 像素坐标一律用美术像素（1 unit = 1 art pixel），逻辑坐标用整数。
- 动画时长对齐参考宠物（见 `docs/design-notes.md` 的时长表），不要做 200ms 就播完的反应动画。

## 许可

提交代码默认按 MIT；提交美术默认按 CC BY-NC-SA 4.0（与仓库现有许可一致）。
