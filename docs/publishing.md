# 发布到社区 / 市场的检查清单

按 dsh-go 的 `docs/design/pets.md`（§3 包格式、§9 素材与许可、市场规范化）和自带 `pet-theme` 技能的
`SKILL.md` 整理。打包前逐条过一遍。

## 1. 素材与授权

- [ ] 所有像素帧、道具、表情都是自己画的，或有明确授权；**不打包第三方素材**（尤其 CC BY-NC-SA 同人图）。
- [ ] `pack-meta.json`（会写进 `pack.json`）的 `author`、`license`、`source` 如实、可核对。
- [ ] 宠物页会显示 `author · license`，并标注「非官方」；README 里也写明非官方。
- [ ] 衍生作品遵守上游许可（本仓库美术为 CC BY-NC-SA 4.0，商用需联系作者）。

## 2. 包结构

- [ ] `pack.json` 在 zip 顶层（不要套多层文件夹）。
- [ ] 只放清单引用到的 PNG；文件名扁平、非点开头、不含 `/`、`\`、NUL。
- [ ] 限制：zip ≤ 64 MiB、条目 ≤ 256、单 PNG ≤ 8 MiB 且边 ≤ 4096、解码 ≤ 16 MiB。
- [ ] 整数几何：`frameW == trunc(Float32(Float32(box.w) * scale))`，画布与帧格都是整数。
- [ ] 确定性 zip：`pack.json` 在前、PNG 排序、固定时间戳、RGBA 重编码且不带元数据（`make build` 已处理）。

## 3. 兼容性

- [ ] `states.idle` 存在；所有引用的动画名都存在。
- [ ] `reactions` 用「基础名 + 编号」字符串写法，不写数组（旧版 App 兼容）。
- [ ] 没把握的字段宁可不写：未知字段会被忽略，旧包也不会因缺省字段被拒。
- [ ] 在真机上导入一次（校验器不能替代 App 导入）。

## 4. 校验

```sh
make build
make check           # 自研校验：导入门 + 市场元数据
make check-official  # 官方 pet_pack_check.py --compat-reactions（pinned commit，需要网络）
make test            # 几何、引用、确定性、包与源码是否同步
```

三项全绿，再打 zip。

## 5. id 与版本

- [ ] `id` 小写字母/数字/`-`，≤48 字符；**发布后保持稳定**——同一个 id 重新导入会替换旧包，改名换 id 会变成两只。
- [ ] 用语义化版本（`v0.1.0`），`CHANGELOG.md` 记录改动；动画增删、时长调整都算需要记录的行为变化。
- [ ] Release 附上 `dist/<id>.zip` 和截图；不要改官方 checker 或伪造校验结果。

## 6. 更新发布

1. 改 `tools/sprite.py` / `tools/build_pack.py` / `pack-meta.json`。
2. `make build && make check && make test`，必要时 `make check-official`。
3. 更新 `CHANGELOG.md` 的版本号与内容，提交并打 tag。
4. 上传 zip 到 Release；在社区帖子里写明：非官方、许可、适用 App 版本、导入方法。
