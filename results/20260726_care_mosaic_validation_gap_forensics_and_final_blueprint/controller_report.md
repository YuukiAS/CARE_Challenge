这次修正后的结论是：0.6965 的 hosted scar 行按用户确认归入 MoSAIC，而且 final MoSAIC repo、final pretrained checkpoint hashes 和 final inference recipe 已经能绑定；不能绑定的是两次历史上传的 exact ZIP bytes/SHA。clean 220-case OOF 仍不支持把 MoSAIC 放进最终 Docker 替代 nnU-Net，排名翻转主要来自 full-data/final-weight submission、validation 域、15 例抽样以及 7/6 到 7/8 的 Cine recipe 调整，而不是 SafeScar、Cascade 或 MMRD 已经有最终分割科学证据。

controller_verification_decision: VERIFIED_COMPLETE

1. exact hosted package/checkpoint/recipe 是否已绑定：final code + final weights + final inference recipe 已绑定到 `IndeedLiu/MoSAIC` commit `d334bd1fb2a99dbbc230510590cd8e3ee08cc377` 和 `/users/a/e/aereinh/MoSAIC/code/weights/download_summary.json` 的 7 个 checkpoint；历史 exact upload ZIP bytes/SHA 仍未绑定。
2. 各因素解释多少：full-data/final-weight inclusion 是主要解释之一；fold0 诊断 lift scar 约 +0.1045 只能当污染/包含效应上界；目标模态结构和 validation 域可部分解释；15-case bootstrap 单独翻正概率 0.0018，不足以单独解释；已观测 scar postprocess 约 -0.0021，不是主因；metric/export 只解释标签/几何边界。
3. Batch7、MMRD、Cascade 独立增量价值：Batch7 只保留候选思想；MMRD 只保留可靠标签/模态卫生；Cascade 无最终 Docker 增量证据。
4. 旧 SafeScar Step3 gate 是否有最终分割科学证据：没有。它是组件级分类证据，不是 final-mask Dice/HD 或 hosted export 证据。
5. 两份 CARE-SER 蓝图保留、删除和修改：保留 nnU-Net baseline、协议卫生和 fallback 原则；删除 MoSAIC/SafeScar/MMRD/Cascade 作为 active runtime mask producer；修改为研究分支需先过 strict clean OOF final-mask gate。
6. 最终 Docker 唯一架构：`NNUNET_ONLY_DOCKER`；病种独立 fallback 是任何非基线组件失败或缺证时保持 nnU-Net identity 输出。
