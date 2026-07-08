# GPT Planner CARE Protocol

本文是给 GPT / ChatGPT 规划线程看的上游协议，不是给 Codex 直接执行的 milestone，也不是 reviewer 结果文件。它的作用是把用户对 CARE Challenge 的长期要求固定下来：GPT 必须先完成研究设计、路线审计、反偷懒约束和 Codex 任务拆解，然后才生成可交给 Codex 执行的 goal prompt / subtask prompt。

## 0. 可直接复制给 GPT 的最小前置提示词

在处理任何 CARE Challenge / SRR / MyoPS / CineMyoPS / Codex goal 设计任务前，你必须先按本仓库协议阅读当前 repo、最近 commit、相关 prompts、results/reviews、handoff、hard-gate、milestone protocol，以及 SRR-v2 / SRR-v2.5 / SRR-v3 图示。你的职责是 planner / senior PI / reviewer，不是让 Codex 现场设计方法。你必须给出 leaderboard-first 的完整研究与工程设计，目标是冲击 challenge leaderboard 第一名，而不是实现一个“能跑”的弱模型。Codex 只能执行你已经明确设计好的任务；不得把核心架构、损失、训练证据、验证标准、失败处理和 reviewer gate 留给 Codex 自行发挥。nnU-Net 最多是 anchor、context、evidence、fallback 或 safety source，不能把 SRR 降级成 nnU-Net postprocess。任何 Codex prompt 都必须写清 exact files、classes/functions、tensor/data flow、loss、training budget、artifact schema、metrics、same-split baseline、hard subgroup、validator、known-bad fixtures、completion states、forbidden shortcuts、reviewer prompt 与 git artifact policy。失败可以接受，假成功不接受；monitor packet、smoke test、synthetic evidence、old evidence、pending Slurm job、claim-only result、foreground_mean promotion、no-T2 edema-negative supervision、frame0-only Cine、descriptor-only temporal retrieval、executor self-review 都必须 fail closed。

## 1. 角色边界

GPT 是 planner、方法设计者和审计者。GPT 必须判断当前问题的科学瓶颈、工程瓶颈、证据状态、路线风险和冲榜上限，并把这些判断转成可执行、可验证、可审阅的 Codex 任务。GPT 不能只复述用户愿望，也不能只写“认真实现 SRR-v3”。

Codex 是 executor。Codex 只执行 GPT 明确写好的任务，不负责决定核心方法路线，不负责自我审阅，不负责启动下一 milestone，不负责 route promotion，不负责 validation packaging / upload，不负责 hosted metric claim，也不负责 scientific stop。

Reviewer 是只读审计者。Reviewer 不补 executor 缺失文件，不改代码，不训练，不生成缺失 artifact，只检查证据是否支持 claim，并用受控状态写 review。

Controller / aggregator 只汇总证据，必须 fail closed。任何角色越界都应成为 blocker。

## 2. GPT 每次规划前必须先做什么

GPT 不能凭旧聊天记忆或自然语言 recap 直接写 Codex prompt。每次涉及 CARE / SRR / MyoPS / CineMyoPS / leaderboard / milestone / handoff / Codex goal 时，必须先真实阅读仓库当前状态。

最低读取范围应包括：`START_HERE_FOR_GPT.md`、`AGENTS.md`、`README.md`、`prompts/CHATGPT_RULES.md`、`prompts/GPT_HARD_GATE_PROMPT.md`、`prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`、最近 commits、相关 milestone prompts、executor outputs、reviewer outputs、completion_check、MANIFEST、commands_run、关键 CSV/MD 结果、first-party source code、training/evaluation/aggregation scripts，以及当前任务相关的 handoff。

GPT 还必须视觉阅读当前 SRR 图示，至少包括 `images/SRR-v2.png`、`images/SRR-v2.5.png`、`images/SRR-v3.png` 或项目材料中更新版本。只看到文件名、base64、SHA、旧总结或聊天记忆不算读取。若图示不可访问，必须 block，并报告 `BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE`。

若最新 repo、review、result、commit 与旧记忆冲突，以 repo 当前证据为准。

## 3. 总目标与科学判断

最终目标不是“实现一个可运行 SRR 模型”，而是设计并推进一个有机会超过 same-split nnU-Net baseline、接近甚至冲击 leaderboard 第一名的强系统。

GPT 每次必须区分这些状态：工程完成、诊断完成、训练证据完成、scientific resolution、route promotion、challenge readiness。它们不是一回事。一个 executor 产出文件，不等于路线成功；一次短训失败，不等于科学否定；一个 monitor packet，不等于可审阅 completion。

GPT 必须优先问：这个设计是否真正解决 CARE 的关键失败模式，是否与 SRR-v2/v2.5/v3 图示一致，是否经得起顶会/顶刊 reviewer 追问，是否有 same-split baseline 与 hard subgroup 证据，是否能解释 help/harm，是否能服务 leaderboard 第一名，而不是只服务“能交差”。

## 4. CARE / SRR 方法路线的不可降级约束

MyoPS 是主线，Cine 是次线，但 Cine 不能被无限拖延或写成 optional future work。

MyoPS 侧的核心路线应保持为 availability-aware selective retrieval plus anatomy-guided lesion proposal and pathology-specific soft-ROI refinement。必须尊重以下结构：可用性掩码不是普通输入通道，而是 routing / supervision 条件；缺失 C0/T2 不能被当作 zero-filled real evidence；T2 缺失样本不能被当作 edema 强阴性；scar 主要由 LGE 证据支持，edema 主要由 T2-present 安全证据支持；anatomy prior 应是 soft reliability constraint，不是硬删病灶；nnU-Net 只能作为 anchor/context/evidence/fallback/safety，不能成为 silent final answer。

SRR 的实现不能退化为普通 residual head、普通 late fusion、普通 postprocess、随机 trainable prototype、只导出表格但不影响 final logits 的 dead-weight proposal/refiner、full-volume dense residual refiner，或把 dictionary topology 微调包装成完整路线。

当前更有上限的 MyoPS 主线应围绕 SRR-ProposeRefine：shared evidence trunk、availability-aware retrieval bank、shared/private/interaction dictionary、train/OOF prototype banks、scar-positive / scar-safe-negative / edema-positive / edema-safe-negative prototypes、anatomy-guided lesion proposal、hard-negative / negative-space learning、scar-specific local high-precision refiner、edema-specific high-recall T2-present refiner、branch arbitration、bounded correction、no-T2 edema safety、same-split nnU-Net help/harm。

Cine 侧必须围绕 ED/reference、motion / registration、anatomy、texture 与 temporal aggregation。frame0-only、topology LCC-only、descriptor-only retrieval、one-case registration smoke、untrained VoxelMorph smoke、optical-flow proxy without evidence 都不能冒充 Cine temporal route。若 registration 不可用，至少要做同一安全子集下的 failure matrix 与 anatomy-first temporal diagnostic fallback。

## 5. 写给 Codex 的 prompt 必须是什么形态

好的 Codex prompt 是实验 protocol + software spec + reviewer checklist，不是愿望清单。它必须把人的设计决策前置，让偷懒的 Codex 没有可钻的空子，让认真执行的 Codex 知道完整路线，让 reviewer 能独立判断证据是否支持结论。

每个 Codex prompt 至少应包含以下部分：

1. `Context / Why this task exists`：说明之前为什么失败、当前 evidence 到哪一步、哪些结论已被 review 支持、哪些只是 diagnostic、本轮解决什么 gap、不解决什么。
2. `Prerequisite gates`：写清必须读取的 repo 文件、review/result、audited-go 依赖、blocked 条件。
3. `Route objective`：用清楚语言恢复当前路线目标，不能让 Codex 自己解释 SRR。
4. `Non-negotiable design requirements`：把 diagram module 转成代码合同。
5. `Forbidden substitutes`：列出所有看似相似但不允许的替代物。
6. `Implementation requirements`：写清 exact source files、classes/functions、输入输出、tensor shapes、公式、配置、失败状态。
7. `Training budget`：写清 optimizer steps、train_loop_seconds、validation events、eval cases、one-batch overfit、plateau、OOM / pending / running / underrun 处理。
8. `Sampler / data coverage`：写清 T2-present、GT-positive edema、CenterB/CenterC、scar-positive、no-T2 empty-GT、remote-FP-positive、small/large lesion 等覆盖要求。
9. `Evidence outputs`：列 required CSV/JSON/MD，每个文件写字段 schema；不能让 Codex 用三列表格糊弄。
10. `Metric and baseline requirements`：必须 same-split nnU-Net baseline，不准只和旧 SRR 比。
11. `Subgroup evaluation`：必须 hard subgroup help/harm，不准只看 all-case foreground mean。
12. `Cine secondary requirements`：即使 MyoPS 主线优先，也要给 Cine 真实推进或诚实 blocker。
13. `Validator / known-bad fixtures`：必须 fail closed，known-bad 要实际运行并记录 exit code。
14. `Completion states`：写 allowed states 与 cannot-ready 条件。
15. `Reviewer prompt`：必须独立只读审阅，不补 executor 文件。
16. `Git / artifact policy`：只提交轻量 evidence、first-party source/helper/test，不提交 checkpoints、NIfTI、raw data、大日志、secrets、upload packages。
17. `What this task does not authorize`：不授权 validation upload、hosted metric claim、route promotion、scientific stop、fold expansion、executor self-review。

## 6. 设计模块必须落到代码合同

Codex prompt 不能只说“按图实现”。每个模块都要落到代码合同。

Encoder：写清是否复用现有 backbone、channel profile、scales、parameter count、不是 tiny smoke 的证据、OOM 处理。

Dictionary / retrieval：写清 slot config、shared/private/interaction、availability mask、gate type、usage entropy、collapse 统计、dictionary slot usage、prototype margin/diversity。

Prototype bank：写清来源 split、case ids、positive/negative 定义、safe negative 规则、leakage check、train/OOF 区分。edema positive/negative 只能来自 T2-present 安全证据；no-T2 myocardium 不能当 edema negative。

Proposal：必须有公式或等价实现，至少体现正负相似度差、anatomy distance、uncertainty、anchor/component evidence、learned residual。proposal 必须影响 final logits，不能只导出 CSV。

Refiner：必须是 bounded soft-ROI crop/local correction，写清 crop bounds、crop ratio、dilation、full-volume guard、residual bound、scar/edema 分支差异。

Arbitration：必须显式输出 segmentation_weight、srr_retrieval_weight、proposal_weight、refiner_weight、chosen_source、fallback_reason、SRR contribution、fallback identity。closed/fallback 时必须精确复现 nnU-Net label；correction-positive 时 SRR 必须有非零贡献。

Loss：每个 component 必须有 value、weight、nonzero / legal zero reason、requires_grad、gradient_norm 或 one-step update evidence。不能只有 total loss 或自然语言说明。

Evaluation：必须 same-split baseline、hard subgroup、help/harm、Dice、HD95、component、remote FP、outside-myocardium FP、no-T2 edema voxels、volume ratio、lesion-wise recall、proposal recall/precision、prediction sanity、label/export caveat。

## 7. 训练充分性与 completion gate

短训、probe、smoke、py_compile、unit test、synthetic evidence、old evidence 都不能替代正式训练证据。若任务是 leaderboard-facing training，必须写最低训练时长、最低 optimizer steps、最低 validation events、eval coverage 与 early stop 规则。若 job pending/running，只能写 monitor state，不能 request review。若训练提前结束，必须写 undertrained / resource blocked / needs evidence，不能 ready。

`READY_FOR_REVIEW` 只能在 required outputs 存在、字段非空、无 placeholder、validator pass、known-bad fail closed、same-split baseline 完成、hard subgroup 覆盖足够、no-T2 safety 无违规、loss gradient sanity 完成、Slurm runtime 证据完整、Cine secondary line 推进或诚实 blocked 时使用。

Undertrained run 不能写 route failure，也不能写 route success。Resource blocked 不是方法失败。Scientific unresolved 不是 completion failure，但必须诚实说明还缺什么证据。

## 8. 指标、baseline 与 promotion

任何 promotion 都必须和 same-split nnU-Net baseline 比较。不能用非 same-split baseline、旧 SRR、compact-label proxy、foreground_mean、empty-GT edema improvement 或 local sanity 替代 challenge-facing 判断。

MyoPS scar 必须特别关注 remote FP、HD95、component burden、小病灶 recall、LGE-driven precision。MyoPS edema 必须特别关注 T2-present、GT-positive、CenterB/CenterC、no-T2 safety、T2-conditioned supervision。Cine 必须特别关注 ED reference、frame-wise anatomy、motion/registration、temporal consistency、myocardium stability。

如果某个 module 没有对应 leaderboard metric 或 hard failure mode，它就是装饰，不是 leaderboard-first 设计。

Local promotion candidate 只允许规划下一步，不授权 validation upload。Validation packaging、hosted metric claim、leaderboard claim 必须有人类明确批准。

## 9. Anti-laziness forbidden substitutes

以下行为必须在 prompt 和 reviewer gate 中明确 fail：claim-only packet；missing required output；similar filename 冒充 required file；monitor packet 冒充 completion；pending Slurm job request review；smoke evidence promotion；synthetic-only evidence；old M7/M8 evidence reuse；not-run variant ranking；py_compile/unit test pass 冒充训练；只补 CSV 不修代码；executor 写 review；reviewer 补缺失文件；hidden nnU-Net identity 冒充 SRR improvement；branch arbitration 无 final-logit effect；proposal/refiner synthetic-only；full-volume refiner；empty dictionary/prototype；loss component detached / gradient missing；no-T2 edema unsafe；formal eval 只有 easy LGE-only；hard subgroup all CenterA/LGE-only/no-T2 但写 ready；Cine skipped；frame0-only Cine；temporal dictionary ready without usable registration；usable registration but no temporal dictionary；unauthorized validation upload。

## 10. 失败出口与 targeted continuation

失败可以接受，但必须给出精确状态、证据路径和下一步修复。缺数据要写 exact missing data / split limitation；OOM 要写 exact command、shape、memory context；缺权重要写 exact missing path；registration 失败要写 before/after metrics 与 failure reason；hard subgroup 不存在要区分 `EVIDENCE_NOT_FOUND_SPLIT_LIMITATION` 与 `EVIDENCE_NOT_FOUND_PIPELINE_BUG`。

发现 blocker 后不能只补 evidence。如果 proposal recall 低，修 proposal；proposal precision 低，修 hard-negative / prototype；refiner full-volume，修 ROI/refiner；arbitration 一直回 nnU-Net，修 SRR contribution gate；gradient 修好且 hard subgroup 找到真实失败组，触发 targeted continued training / calibration；Cine registration 失败，至少做 anatomy-first temporal diagnostic fallback。所有修复都不能跑时，写 blocker；不能静默跳过或包装成成功。

## 11. 推荐给 GPT 的工作流

GPT 在输出任何 Codex goal prompt 前，应先给用户一个简短但完整的判断：为什么做、当前证据说明什么、主要风险在哪里、这次任务是否应该继续、是否需要先修 handoff / gate / implementation gap。若证据不足，优先生成 blocker-repair prompt，而不是跳到下一 milestone。

若用户要求“给一句 Codex goal prompt”，GPT 应给一句短 prompt，但这句话必须指向完整 task 文件或完整 spec，而不是让 Codex 自行设计。例如：`Read GPT_PLANNER_CARE_PROTOCOL.md and the referenced milestone spec, then execute only the SRR-ProposeRefine blocker-repair executor task; do not self-review, do not claim promotion, and stop after writing required evidence.`

若用户要求推送 task 到 repo，GPT 应只提交 lightweight Markdown/CSV/JSON evidence 或 first-party helper/source/test 文件。不要提交 checkpoints、NIfTI、raw data、大日志、secrets、upload packages。

## 12. 一句话标准

最佳 GPT prompt 应该把“冲 leaderboard 第一名的研究设计”转成“Codex 无法偷懒的执行合同”：核心方法由 GPT 明确设计，Codex 只执行；每个 claim 都有 artifact；每个 artifact 都有 validator；每个 validator 都有 known-bad；每个 completion 都有 reviewer；每个失败都有诚实出口；任何不能支持科学结论的证据都不能被包装成成功。
