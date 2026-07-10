# CARE 当前模型架构

本页记录当前架构状态，供规划者和 mapper/reviewer 使用。它不是路线晋级结论。

## MyoPS

当前 SRR-ProposeRefine 相关一方代码主要在：

- `src/care_myocardium/models/srr_propref.py`
- `src/care_myocardium/models/srr_blocks.py`
- `src/care_myocardium/losses/srr_losses.py`

目标路线仍是 SRR-v3：availability-aware selective retrieval、semantic representation retrieval bank、anatomy-guided lesion proposal、scar/edema pathology-specific soft-ROI refinement，以及 explicit objectives。`nnU-Net` 只能作为 anchor、context、evidence 或 safety source，不能把 SRR 降级成普通后处理。

M9 follow-up 的证据已经完成一致性修复并通过独立 review，但结论仍是 `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`。这表示当前 formal SRR-main candidates 没有超过 tracked M8 `nnU-Net` anchor；它不等于 SRR 路线被科学证伪。

## Cine

Cine 是必做次线。当前证据仍是 local proxy final-output evidence。没有 validation upload、hosted metric claim、route promotion、fold expansion、scientific stop 或 M10 启动授权。

## 当前限制

- `controller_supervision` 和 `mapper_wiki_observability` 仍是 `partial/unverified`，直到出现真实 controller runtime evidence。
- 历史 M8/M9 分析在 `wiki/history/` 中保存，不作为 current runtime evidence。
- 架构变化后必须重新生成图并运行 `validate_care_architecture_wiki.py --strict --history`。
