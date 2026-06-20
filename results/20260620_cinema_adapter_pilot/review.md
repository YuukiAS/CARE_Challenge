# Review 20260620 Cinema Adapter Pilot

decision: OPEN_NEXT_TASK

## 结论

该 legacy result 已按当前 protocol 迁移到 `results/20260620_cinema_adapter_pilot/`。从已有 result 看，本轮已完成隔离 CineMA -> CARE CineMyoPS adapter pilot，并保留了命令、日志、job id、输出路径、指标和失败修复记录。

## 完成度判断

- task 目标：建立并运行隔离 CineMA 到 CARE CineMyoPS anatomy adapter/pilot。
- result 覆盖情况：已覆盖读取文件、修改文件、运行命令、Slurm job、测试结果、主要指标、失败信息、git diff 摘要和下一步建议。
- 未完成部分：未做 official validation upload，也未纳入主训练 pipeline；这些均符合原 task 禁止动作。

## 证据检查

- 文件证据：`results/20260620_cinema_adapter_pilot/result.md` 列出新增脚本、job、note 和输出目录。
- 命令证据：result 记录了 clone、pip install、diagnostic、adapter、Slurm 和 py_compile 命令。
- 产物证据：`results/20260620_cinema_adapter_pilot/MANIFEST.md` 索引了 task、result、review 和原有 output roots。
- 指标证据：result 记录了 train frame0/ED 与 all selected frames 的 myocardium/LV Dice 和 HD95。

## 权限与边界检查

原 task 授权联网、shell 和隔离新增文件；禁止外部上传、validation package、主训练入口修改和高风险配置。已有 result 显示这些边界被遵守。

## 风险与遗漏

本 review 是协议迁移时基于已有 result 的复盘，没有重新运行 pilot。大产物仍保留在 CARE 既有 domain-specific result roots，并通过 manifest 索引。

## 下一步

建议开下一张 task：保持 adapter 隔离，优先做 geometry-aware foreground/heart crop 或比较 CineMA `mnms`/`mnms2` checkpoints，不直接改主 training pipeline。
