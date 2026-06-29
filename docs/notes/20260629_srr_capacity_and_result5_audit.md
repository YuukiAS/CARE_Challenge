# 20260629 SRR capacity、Result5执行结果与下一轮修复判断

本轮结论是：Result5的方向没有被实验否定，但当前实现没有足够能力与训练/解码管线去承载这个方向。问题不能解释成“proposal/refinement思想错了”，更应解释成三层叠加：第一，当前SRRMyoPSLite仍是单尺度浅层证据头，容量和空间建模远弱于nnU-Net；第二，Result5 proposal没有真正形成独立候选生成与soft-cascade refinement，而是把prototype proposal logits混回最终全图logits；第三，训练、解码、checkpoint选择与ignore-label masking存在实际管线问题，导致结果可能被压在0.1 Dice量级附近。

当前代码事实非常明确。`src/care_myocardium/models/srr_myops.py` 中，三个modality-specific stems都只有一层3D卷积、GroupNorm和LeakyReLU。三个stem输出随后经 `masked_modality_fusion` 先按availability平均成一个 fused feature，再送入 `SRRRetrievalBlock`。因此，private expert虽然在mask层面按模态可用性开关，但专家本身吃的是同一个 fused feature，不是真正的LGE-private、T2-private、C0-private特征流。`SRRMyoPSLite` 没有四尺度encoder-decoder、没有下采样/上采样、没有skip connections，也没有完整nnU-Net式decoder。所谓 multiscale_dictionary 只是对 fused feature 做一次avg_pool3d，再上采样回原尺度混合，不是完整多尺度表示学习。

proposal实现也只是半步。`PathologyProposalHead` 确实加入了正负prototype similarity、local anatomy confidence、uncertainty，但它最终把 `0.40 * original + 0.60 * proposal` 直接写回 `scar_logits` 和 `edema_logits`。这意味着 proposal 当前仍是final-logit shaping，不是Result5要求的候选区生成器。真正的soft-ROI refinement还没有正式训练；`20260629_true_soft_roi_refine` 只验证了几何preflight，状态仍然是等待proposal route选择。

结果层面也支持这个解释。`20260626_dict_bank` 选出了 `cross_modal_interaction_dictionary`，说明dictionary/retrieval不是随机噪声；但该路线仍然HD95、component count和remote FP高。`20260626_lesion_compact` 没有选出compactness package，说明在proposal不可靠时加几何损失只会在Dice和HD之间互相牺牲。`20260628_myops_proposal` 的三条formal proposal variants全部跑完，但selection是 `REVISE_PROPOSAL_AND_REPEAT`，不是 `SELECT_PROPOSAL_ROUTE`。其中 `proposal_uncertainty_gate` 给出最好的edema GT-positive Dice 0.2034和all-case Dice 0.4376，但HD95仍高；scar最佳all-case Dice只有0.1017，甚至低于D4字典参考0.1054。

续跑审计进一步暴露了实现/训练问题：ignore-label loss masking bug已经被确认并修复到未来 runs；decode calibration显示 raw argmax 不是合适的最终表面，threshold sweep能从现有checkpoint恢复额外信号；checkpoint selection显示patch-loss best checkpoint并非pathology-optimal；hard-negative mining已经挖出7237个FP components，其中scar replay-safe 4167、edema replay-safe 1561，但尚未进入formal replay training；true soft-ROI refinement只做了几何验证，未正式训练。

因此，下一轮不应简单继续同一个轻量SRRMyoPSLite。必须同时走两条路线。第一条是短周期管线修复和repeat：用已确认的loss masking、decode calibration、pathology-aware checkpoint selection、hard-negative replay和uncertainty gating重跑proposal，验证当前弱信号是否可被恢复。第二条是结构重建：实现一个真正接近图和Result4/Result5的SRR-v2，即nnU-Net-like multi-scale encoder-decoder、true modality-private feature streams、多尺度retrieval bank、pathology-specific proposal/refinement heads。若SRR-v2仍无法接近nnU-Net，则应启动baseline-preserving cascade/teacher route，把nnU-Net或anatomy-first coarse output作为第一阶段强空间先验，再让SRR承担缺模态与pathology-specific refinement，而不是让弱SRR独自替代nnU-Net。

本审计支持新增 `20260629_srr_v2_unet_core.md`。原因是encoder/decoder确实是高概率瓶颈之一。当前模型与图中的多尺度encoder-decoder+retrieval bank+soft-ROI refinement相差较大；在这样的轻量架构上继续堆proposal和loss，很难公平判断Result5思想是否能超过nnU-Net。下一批goal必须把“结构容量是否不足”作为一条正式实验线，而不是只做小修补。
