
这次结论很直接：0.6965 的 hosted scar 行按用户确认归入 MoSAIC，但本地没有找到能绑定该行的 exact validation zip、checkpoint 和 inference command；clean 220-case OOF 不支持 MoSAIC 替代 nnU-Net。排名翻转主要应解释为 full-data inclusion/selection、validation 域与 15 例抽样共同作用，再叠加未解析的 exact recipe，而不是 SafeScar、Cascade 或 MMRD 已经有最终分割科学证据。

controller_verification_decision: VERIFIED_COMPLETE

1. exact hosted package/checkpoint/recipe 是否已绑定：未绑定。模型家族已按用户确认固定为 MoSAIC；exact zip SHA、checkpoint 组合、TTA/threshold/postprocess/reconstruction 命令仍为 `UNRESOLVED`。
2. 各因素解释多少：full-data inclusion/selection 有 fold0 诊断 lift，scar 约 +0.1045；已观测 scar postprocess 约 -0.0021，不能解释提升；target modality/domain 和 15-case 波动是部分解释但没有 validation GT；metric/export 只解释边界，不解释大幅提升；exact recipe 未解析。
3. Batch7、MMRD、Cascade 独立增量价值：Batch7 只保留候选思想；MMRD 只保留可靠标签/模态卫生；Cascade 无最终 Docker 增量证据。
4. 旧 SafeScar Step3 gate 是否有最终分割科学证据：没有。它是组件级分类证据，不是 final-mask Dice/HD 或 hosted export 证据。
5. 两份 CARE-SER 蓝图保留、删除和修改：保留 nnU-Net baseline、协议卫生和 fallback 原则；删除 MoSAIC/SafeScar/MMRD/Cascade 作为 active runtime mask producer；修改为研究分支需先过 strict clean OOF final-mask gate。
6. 最终 Docker 唯一架构：`NNUNET_ONLY_DOCKER`；病种独立 fallback 是任何非基线组件失败或缺证时保持 nnU-Net identity 输出。
