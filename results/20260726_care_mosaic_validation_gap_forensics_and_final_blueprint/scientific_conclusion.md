220-case clean OOF scar 的 MoSAIC 均值为 0.392438，nnU-Net 均值为 0.577502，差值为 -0.185063。这个 clean OOF 与 hosted scar 0.6965 的反差，不能再解释为“MoSAIC lineage 未绑定”：现在 final repo、final weights 和 final recipe 已绑定；真正未绑定的是当时上传 ZIP 的 bytes/SHA。

更合理的解释是：hosted row 使用 MoSAIC final/full-data submission 权重和 final/near-final inference recipe，和 clean OOF 的训练域不同；7/8 相比 7/6 的主要可见变化在 Cine 分支，符合 repo 中 V1/V2 previous-best ensemble 从 0.1878 提升到约 0.2069 的注释。即便如此，clean 220-case OOF 仍不支持 MoSAIC、SafeScar、MMRD 或 Cascade 作为最终 Docker 主动分割组件。唯一可执行架构仍是 `NNUNET_ONLY_DOCKER`，病种独立 fallback 为保持 nnU-Net identity 输出。
