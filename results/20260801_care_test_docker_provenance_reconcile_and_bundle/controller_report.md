# Controller Report

这次不是因为 rootless Docker，也不是因为上一轮完整六类 mismatch 直接停下。新的审计先把标签编码统一后重算：package A 与上一轮 fresh nnU-Net 的 geometry 为 15/15，一致的完整数组为 4/15，生产会使用的 `1/2/3/4` 通道也只有 4/15。11 个不一致病例合计只有 120 个语义体素变化，但变化横跨 anatomy、pure edema、scar 和背景，不能说成只是不使用的 scar 通道差异。

历史追溯没有找到能 exact 复现 package A 的 variant。按合同执行了三个冻结 replay：`checkpoint_final + default TTA`、`checkpoint_best + no TTA`、`checkpoint_final + no TTA`，三者均未达到 full-array 或 used-channel 15/15 exact。因此历史 `0.6691` lineage 保持 `UNRESOLVED`，且 `historical_0_6691_claim_authorized=false`。

随后对当前部署源 `checkpoint_best.pth + folds 0-4 + default TTA` 做第二次独立 fresh replay。两次 replay 的 geometry 是 15/15，但 array 只有 7/15 完全一致，合计 13 个体素变化。合同规定只有这种“当前部署 source 自身两次推理不一致”才允许再次阻塞；所以本任务终态为 `SERVER_BUNDLE_BLOCKED`，阻塞 token 为 `NNUNET_DEPLOYABLE_SOURCE_NONDETERMINISTIC`。

未继续生成 MyoPS production bundle、sentinel、transfer tar 或 `SERVER_BUNDLE_READY.json`。MoSAIC Cine 没有作为新的阻塞理由扩大执行；停止点已经在 W4 的 nnU-Net 部署源复现性门。未 sudo、未系统安装、未 Docker/rootless、未上传网盘/validation/Docker、未给组织方发邮件、未作 hosted metric claim。
