# CARE table review notes

## 写作边界
- 本轮只写 `docs/presentation/2026_08_01_care_group_meeting/` 下 10 个文件；未训练、未提交 Slurm、未 commit、未 push。
- `care_teacher_facing_tables.md` 是组会投屏版：中文结论先行，只保留必要模型名、病例号和指标名；完整路径、哈希、验证器字段和可比性枚举仍以证据总表/来源台账为准。
- `care_metric_comparison_tables.md` 是指标总表投屏版；`care_training_metric_comparison.csv` 和 `care_validation_metric_comparison.csv` 是备用数据表。
- `git pull --ff-only origin main` 后 HEAD 为 `23d12d51a039c215a2ccdbb46477c5cf517eb656`，远端已是最新。
- 工作树开始时已有 4 个未跟踪文件/目录，本轮不清理、不覆盖。

## 视觉核查
- 已用本地图像查看器核查 `Case2019`, `Case2034`, `Case2021`, `Case3010`, `Case3036` 的 v3 atlas PNG；图像与数值表一致地显示 MoSAIC clean 与 nnU-Net/full-final recipe 的显著差异。
- `Case3008`, `Case3009`, `Case3027`, `Case2012` 未在 `v4_atlas_manifest.csv` 中找到可定位 atlas；hard-case 表写 `page unresolved`，没有猜页码。

## 无法确认字段
- Hosted hidden validation 没有本地 GT/prediction，不能确认 case-wise hard-case 表现。
- MoSAIC hosted exact ZIP hash 未在本地完全绑定；使用 user-attested/repo-weight-recipe boundary。
- CARE-DG 行没有可与 clean OOF 同尺度直接比较的单一 summary Dice；保留为机制/数据域诊断。
- `edema-zone` 历史指标不能转写成 official pure edema。
- `/tmp` live leaderboard 与仓库 latest CSV 不完全一致；为了遵守输出目录限制，未改写 `results/leaderboard`。

## 自动检查结果
- CSV 每行 source path、comparability 枚举、必需 hard cases、Markdown/CSV 行数、禁用词和 source 文件存在性检查通过。
- 主表 24 行；hard-case 表 9 行。
- 指标备用 CSV 可解析：training 表 12 行、validation 表 4 行。
- `Case3008`, `Case3009`, `Case3027`, `Case2012`, `Case2019`, `Case2034`, `Case2021` 均已覆盖；另含历史视觉对照 `Case3010`, `Case3036`。
- `git diff --check` 无输出，退出码 0。
- `git diff --stat` 无输出，因为本轮输出文件未 staged、仍为 untracked；自定义检查已覆盖新文件内容。
- 最终 `git status --short` 除本轮 `docs/presentation/` 外，还显示若干无关 untracked 文件/目录；本轮未清理、未覆盖。
