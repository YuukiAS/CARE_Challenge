# soft-ROI refiner

> 历史快照：M08。本页只保存从 `TODO.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

### 1.6 Soft ROI refiner：有实现，但实际是小 crop residual，不是完整 lesion formation engine

`CropSoftROIRefinementHead` 是实打实实现了的。它先用 proposal、proposal context、anchor evidence、component evidence、anatomy gate、uncertainty、distance support 形成 soft ROI；然后对每个 case 取 bounded crop，把 features、原图 modality crop、evidence logits、proposal logits、anatomy prior、anchor/component evidence、pos/neg similarity、uncertainty、distance、ROI、P_union/LV/RV、distance maps、task gate 等一大串输入拼起来，跑一个小 conv residual head，再 paste 回 crop。

这不是“完全没做 refiner”。但它的能力边界很窄：它是局部 residual，不是一个新的 full-resolution lesion generator；它的输出最终还要经过 baseline-preserving arbitration；如果 proposal 或 gate 不打开，它的作用就被稀释。M8 follow-up 的 proxy table 就显示 conservative fallback 根本没有启用 SRR case，高信号 fallback 启用了也只给 scar 微弱收益、edema 伤害。
