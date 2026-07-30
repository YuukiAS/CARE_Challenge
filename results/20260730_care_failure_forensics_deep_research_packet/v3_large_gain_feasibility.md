# 约 0.1 Dice 级增益可行性终审

本地 clean held-out 证据不支持 simple ensemble 或 case selector 达到约 0.1 Dice。nnU-Net + MoSAIC 的 case-oracle gain 对 scar 只有约 0.02 量级，对 pure edema 约 0.00 量级；voxel oracle 只说明错误体素中存在可分割空间，不是可部署模型上限。

当前结论：LOCAL_EVIDENCE_SUPPORTS_ONLY_MODEST_GAIN。

若要追求约 0.1 Dice，需要新机制直接攻击大误差池，例如小病灶 FN、remote FP、边界 undersegmentation、no-T2 supervision hygiene、center/domain calibration 和 decoder capability preservation。该机制必须先通过 patient-level feature probe、error-pool ablation 和 clean validation evidence，而不是复用历史未进入 final logits 的组件。
