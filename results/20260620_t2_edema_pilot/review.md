# Review 20260620 T2 Edema Pilot

decision: OPEN_NEXT_TASK

## 结论

该 legacy result 已按当前 protocol 迁移到 `results/20260620_t2_edema_pilot/`。从已有 result 看，本轮完成了覆盖 80 个 T2-present complete cases 的 edema feature/routing pilot，并给出了明确的下一步方向。

## 完成度判断

- task 目标：判断 `myops_edema` 是否应从统一 zero-filled missing-channel 训练转向 complete-case T2-aware expert/routing。
- result 覆盖情况：已覆盖数据机制复核、feature baseline、指标、脚本/job、输出路径、失败信息和下一步建议。
- 未完成部分：没有启动 GPU training，也没有进入正式 pipeline 或 submission；result 已说明这是受任务边界限制后的 fallback。

## 证据检查

- 文件证据：`results/20260620_t2_edema_pilot/result.md` 列出读取文件、修改文件和输出目录。
- 命令证据：result 记录了 py_compile、bash -n 和正式 pilot 命令。
- 产物证据：`results/20260620_t2_edema_pilot/MANIFEST.md` 索引了 task、result、review 和原有 experiment output root。
- 指标证据：result 记录了 fold0 complete val Dice、precision、recall、HD 和 HD95。

## 权限与边界检查

原 task 禁止联网、external upload、official validation submission、删除数据和主训练入口修改。已有 result 显示这些边界被遵守。

## 风险与遗漏

本 review 是协议迁移时基于已有 result 的复盘，没有重新运行 pilot。大产物仍保留在 CARE 既有 `results/experiments/` root，并通过 manifest 索引。feature baseline 不等同于正式 T2 expert training。

## 下一步

建议开下一张 task：使用现有 nnU-Net501 representation 做 baseline-preserving complete-case edema expert 或 class-4 residual head；no-T2 cases 不应作为 class-4 hard negative。
