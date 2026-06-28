# 20260628 Result5 计划复盘与下一轮任务设计说明

Result5 的关键结论不是继续把 SRR dictionary 当作最终分割器，而是把它降位为第一阶段 evidence engine。当前 SRR 已经学到“该看哪些模态证据”，所以不同 dictionary 结构会稳定改变 scar 与 edema 的表现；但它还没有学到“病灶如何在空间上形成”，因此无法稳定降低远端假阳性、component burden 和 HD95。Result5 明确建议把现有 SRR 升级为“共享证据干线 + 病种专属 proposal dictionary + soft-cascade refinement”的系统，并加入正负原型判别与 hard negative mining。

这和上一轮自己的判断一致，但 Result5 更完整、更强。此前的判断只是说 dictionary 应从 feature selection 升级到 lesion proposal 和 negative prototype；Result5 进一步明确了可执行结构：SRR 作为 evidence trunk，输出 anatomy prior、scar/edema evidence map 和 uncertainty；scar 与 edema 分别建立 proposal dictionary；proposal logit 不再由普通 dense head 自行学习，而由 positive prototype 与 negative prototype 的相似度差、anatomy prior、remote distance penalty 和 evidence map 共同决定；然后在 soft ROI 内做 refinement。这个设计比继续调 compactness loss 更合理，因为 compactness 在 proposal 不可靠时只能压缩错误 logit 场，容易用牺牲 Dice 换 HD。

Result5 还指出，现有示意图没有显式把 anatomy 结构纳入病灶生成，这是当前系统性缺口。下一轮任务必须让 anatomy prior 进入模型的数据流，而不只是把 myocardium 当作另一个 segmentation 输出。正确方向是让 anatomy 生成 soft union prior、distance map、ROI proposal 和 refinement crop 条件。对 scar，ROI 应更小、更高分辨率、更强 hard negative；对 edema，ROI 应更大、更保留上下文、更重视 T2-present recall 和 uncertainty。

CineMyoPS 方面，Result5 的判断也很明确：当前 keyframe context retrieval 没有正信号，不等于时序无用，而是因为非 reference frame 没有通过 motion registration 或 warping 对齐到 reference frame。下一轮 Cine 不能继续只看 frame 或简单聚合 keyframes，必须引入 reference-frame registration/warping。可以允许下载或安装网络资源，但必须把候选配准模块作为可替换资源进行比较，优先考虑 SimpleITK/ANTsPy/NiftyReg/VoxelMorph/现有 cardiac motion 思路中能快速落地的方案。

关于旧任务，`20260626_dict_research.md`、`20260626_dict_bank.md`、`20260626_lesion_compact.md`、`20260626_cine_temporal.md` 和 `20260626_next_goal.md` 不再作为未来入口，但应保留为历史证据，因为对应结果已经写入 `results/20260626_*` 并被后续判断引用。新的执行入口应是 `prompts/tasks/20260628_result5_goal.md`。
