# SRR-v3 Executor Prompts

Copy exactly one section into the main Codex executor/controller session. The executor must commit locally and stop. The user manually pushes.

## Agent-flow v2 executor/controller rule

For new CARE work, `prompts/AGENT_FLOW_V2_PROTOCOL.md` is the canonical source. Use role names `planner`, `controller`, `executor`, `mapper`, `finalizer`, `validator`, and `reviewer`. Historical `auditor` wording in older sections means the independent read-only `reviewer`; do not create a controller-internal auditor subagent.

Short work may be `execution_mode: direct_executor`. Overnight, long Slurm, multi-job, or high-resume-risk work must be `execution_mode: controller_supervised`, must use the Slurm routing skill before job submission, and must have durable continuity via `slurm_dependency` or `tmux_watcher`. A controller must obey GPT-authored `executor_slots` and `mapper_slots`; default is one executor and one mapper.

If `architecture_impact` is `component` or `system`, invoke the mapper contract in `.agents/skills/care-mapper/SKILL.md` and update root `wiki/` artifacts unless the task explicitly provides a no-change fingerprint receipt. The finalizer is deterministic terminal accounting, aggregation, validation, wiki finalization, and commit; it is not a reviewer and must not write `review.md`.

## Local commit rule for every milestone

At goal completion, the executor must create one local commit containing every small file needed for the separate reviewer to inspect the milestone. A milestone goal is not complete merely because files exist locally under an ignored `results/20??????_*` directory; the reviewer must be able to recover the required evidence from git after the user pushes the commit.

The commit must include the milestone required outputs, `result.md`, `completion_check.md`, `review_request.md`, `MANIFEST.md`, small Markdown/CSV/JSON evidence tables, and any small first-party helper/source/config files needed to reproduce or interpret the evidence. Use `git add -f` for ignored `results/20??????_*` milestone packets. If any required review evidence is intentionally not committed, the executor must state the exact reason in `result.md`, `completion_check.md`, and `MANIFEST.md`; otherwise omission of necessary review evidence is a protocol violation.

This rule applies to every milestone and continued milestone prompt in this file. If a milestone-specific section omits or abbreviates the local commit instruction, this global rule still controls, and the goal remains incomplete until the required reviewer evidence has been committed locally.

Do not commit checkpoints, NIfTI predictions, upload packages, large logs, raw data, secrets, environment dumps, or whole runtime result trees. Do not push; the user manually pushes.

## MONITOR_PACKET_IS_NOT_COMPLETION

This rule applies to every milestone, continued milestone, M7 follow-up2/follow-up3, and future follow-up prompt in this file.

Submitting a Slurm job, monitor job, watcher, or pending packet is not completion. If the executor has only submitted a job or written a monitor packet, it must not write milestone ready, must not write a normal `review_request.md`, and must not claim the goal complete.

If `completion_check.md`, `result.md`, `commands_run.md`, or any `followup*_training_adequacy.csv` / adequacy table contains `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent monitor/pending state, completion must be `NEEDS_MONITOR` or `NEEDS_EVIDENCE`, not ready.

After the job completes, the executor must rerun the relevant aggregator or evidence collector and commit tracked lightweight evidence files derived from runtime outputs before requesting review. `commands_run.md` entries that only show `sbatch submitted`, `squeue pending`, `PENDING Priority`, or pending `sacct` do not count as completion evidence.

Every job-derived completion packet must record `job_id`, `state`, `exit_code`, `runtime`, `log_path`, `runtime_output_path`, `aggregation_command`, `aggregation_exit_code`, and the tracked evidence files updated from runtime output. If the job completed but runtime output cannot be found or the aggregator fails, write `NEEDS_EVIDENCE`, not ready.

## Global executor rule

```text
这是单个 milestone 的 executor/controller session。只执行当前 milestone。goal 完成前必须用 git add -f 提交供 reviewer 审阅所需的全部轻量证据文件；只把文件留在本地 ignored results 目录里不算完成，因为 reviewer 在用户 push 后必须能从 git 中恢复证据。提交范围包括 required outputs、result.md、completion_check.md、review_request.md、MANIFEST.md、小型 Markdown/CSV/JSON 证据表，以及生成或解释这些证据所需的小型 first-party helper/source/config 文件；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets、environment dumps 或整个 runtime result tree。如果任何 reviewer 必需证据不提交，必须在 result.md、completion_check.md 和 MANIFEST.md 写清具体原因，否则视为 protocol violation。MONITOR_PACKET_IS_NOT_COMPLETION：仅提交 Slurm job、monitor job、watcher 或 pending packet 不算完成；含 NEEDS_MONITOR、PENDING_MONITOR、JOB_SUBMITTED、PENDING_PRIORITY、RUNNING、AWAITING_SACCT 或等价状态时不能写 ready，必须等 job 完成后重新运行 aggregator/evidence collector 并提交 tracked lightweight evidence。不要 push，由用户手动 push。随后停止；不要写 review.md、不要批准自己、不要启动下一个 milestone。必须由另一个独立只读 Codex reviewer 写 review.md 并给出 audited-go 后，才允许进入下一 milestone。
```

## M0 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md。这是架构契约 milestone，不训练、不改模型、不跑后续 milestone。先读取 handoff hard-gate repair review、SRR-v2.5 evidence supplement audit、HANDOFF_GATE_POLICY、GPT_HARD_GATE_PROMPT、MILESTONE_REVIEW_PROTOCOL；确认 hard-gate repair 是 AUDITED_GO。然后在 results/20260705_srr_v3_m0_architecture_master_contract/ 写齐 required outputs、completion_check.md、review_request.md 和 MANIFEST.md。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M1。
```

## M1 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md。开始前必须确认 results/20260705_srr_v3_m0_architecture_master_contract/review.md 存在且包含 M0_AUDITED_GO，否则停止。目标是补足运行时证据，不训练新模型：导出 gate open-rate、bounded delta、gate*delta、decode label delta、anchor confidence、prototype T2-present coverage、anchor/component alignment、no-T2 safety。结果写入 results/20260705_srr_v3_m1_runtime_instrumentation_gate/。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M2。
```

## M1 executor (continued)

```text
继续执行 prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md 的 M1 evidence revision，不是 M2。开始前必须确认 results/20260705_srr_v3_m0_architecture_master_contract/review.md 包含 M0_AUDITED_GO，并确认 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md 包含 M1_AUDITED_NEEDS_EVIDENCE；如果不是这个状态，停止并报告。只修复 M1 reviewer 指出的 blocker：prototype_coverage_export.csv 中 edema_positive=0、edema_negative=0、t2_present_edema_positive=0 / EDEMA_PROTOTYPES_EMPTY。目标是构建或选择一个可审计的非空 T2-present edema prototype source，并重新导出 M1 instrumentation evidence：gate_residual_export.csv、prototype_coverage_export.csv、anchor_context_alignment_export.csv、no_t2_safety_export.csv、runtime_instrumentation_summary.json、commands_run.md、instrumentation_unit_tests.md、result.md、completion_check.md、review_request.md 和 MANIFEST.md。允许小型 first-party helper/source/config 修改来生成或解释这些证据；不允许训练新模型、full-fold training、validation packaging/upload、route promotion、M2 execution，不能把 EVIDENCE_NOT_FOUND 或 claim-only CSV 当作 completion pass。必须运行 strict validator；如果 prototype coverage 仍为空或 strict validator 失败，completion_check.md 写 M1_NEEDS_EVIDENCE 并停止；只有在非空 T2-present edema prototype coverage 和 M1 required exports 都通过 strict validation 时，completion_check.md 才能写 M1_READY_FOR_REVIEW。完成后用 git add -f 提交 M1 continued packet 供 reviewer 审阅所需的全部轻量文件和必要 helper/source/config；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets、environment dumps 或整个 runtime result tree；不要 push，由用户手动 push。不要写 review.md，不要批准自己，不要启动 M2。
```

## M2 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md。开始前必须确认 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md 存在且包含 M1_AUDITED_GO，否则停止。目标是修复 MyoPS 运行时架构缺口，只允许小规模 smoke，不允许 full-fold training：closed gate 要精确复现 nnU-Net，同时要有 correction-positive gate opening sanity；strong encoder/context 要有现实可运行证据；prototype bank 必须包含 T2-present edema 正负证据；proposal/refinement 必须有 bounded local ROI 证据；no-T2 edema 必须端到端安全。结果写入 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M3。

开始前必须确认 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md 存在且包含 M1_AUDITED_GO；如果不满足，停止并写 M2_BLOCKED_BY_M1，不要做任何科学任务。

这是单个 milestone 的 executor/controller session。目标是修复 MyoPS SRR-v3 runtime architecture，使后续 M3 minimum-effective pilot 能训练真实 baseline-preserving bounded correction，而不是继续 near-identity diagnostic packet。允许修改模型、训练、评估和 instrumentation 代码；允许 toy/small-case smoke、one-batch overfit 和 explicit hard-subgroup eval；禁止 full fold training、validation packaging/upload、route promotion、hosted metric claim、scientific stop，也不要启动 M3。

必须关闭并证明以下 runtime gaps：

Baseline-preserving anchor/residual safety：closed gate 必须精确复现 nnU-Net；同时要有 correction-positive sanity，证明 gate 能在 synthetic uncertain/error region 上打开，并且 correction bounded。
Strong encoder/context path：strong_4scale 必须在现实 channel setting 下可调用，或给出 memory-safe alternative；不能只用 tiny base_channels=4 smoke 当证据。
Pathology proposal/refinement path：scar 和 edema proposal 必须进入 bounded local ROI refinement，并按 class 输出 proposal/refinement diagnostics；不能把 full-volume residual 叫 local refinement。
Real prototype/dictionary evidence：prototype fitting 必须选择包含 T2-present edema-positive 和 edema-safe-negative 的 train subset；如果 selected subset 没有 T2-present edema evidence，必须重新选 subset 或停止为 M2_NEEDS_EVIDENCE。不要使用 edema prototype bank 为零的 checkpoint 作为通过证据。
No-T2 edema safety：loss、proposal、ROI、final logits、decode、export 必须对 no-T2 case 端到端 blocked 或 safely inert。
Cache/provenance isolation：每个 smoke 输出必须记录 checkpoint path、prototype source、selected case ids、encoder profile、optimizer steps、eval case ids、运行命令和 artifact path。

结果写入 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/，必须写齐：

result.md
code_diff_summary.md
runtime_gap_closure_table.csv
strong_encoder_context_sanity.csv
prototype_t2_coverage_sanity.csv
proposal_refinement_sanity.csv
baseline_gate_safety_sanity.csv
no_t2_safety_sanity.csv
unit_test_report.md
completion_check.md
review_request.md
MANIFEST.md

Unit tests 必须覆盖 closed-gate identity、synthetic correction-positive gate opening、T2-present prototype selection、no-T2 edema blocking、bounded local crop behavior。runtime_gap_closure_table.csv 中每个 required runtime gap 必须标成 CLOSED、PARTIAL 或 NEEDS_EVIDENCE，并给出 exact artifact path。运行并记录 default strict validator。

M2 completion_check 只能写 M2_READY_FOR_REVIEW、M2_NEEDS_REVISION 或 M2_NEEDS_EVIDENCE。如果 T2-present edema prototype bank 仍为空、gate statistics 仍不可用、local refinement 没有 bounded-crop 证据、或 no-T2 edema safety 不是端到端导出，不能写 ready。
```

## M2 executor (continued)

```text
继续执行 prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md 的 M2 provenance/cache revision，不是 M3。开始前必须确认 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md 包含 M1_AUDITED_GO，并确认 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md 包含 M2_AUDITED_NEEDS_REVISION；如果不是这个状态，停止并报告。只修复 M2 reviewer 指出的 blocker：cache/provenance isolation 被标成 CLOSED，但 runtime_smoke_summary.json 没有显式记录 task 要求的 checkpoint path、prototype source、selected case ids、encoder profile、optimizer steps、eval case ids 等字段。

不要重新设计模型，不要扩大训练，不要 full-fold training，不要 validation packaging/upload，不要 route promotion，不要 hosted metric claim，不要启动 M3。除非为了生成或验证 provenance 字段必须做最小代码/validator 修改，否则不要改动已通过 review 支持的 runtime repair 逻辑。允许重跑 M2 bounded smoke/instrumentation helper；如果 helper 是 no-training smoke，必须把 checkpoint_path 明确记录为 N/A_NO_TRAINING_SMOKE 或同等明确值，把 optimizer_steps 明确记录为 0，并记录 smoke mode。

必须使 provenance/cache evidence 在单个可审计 artifact 中直接可见，优先更新 runtime_smoke_summary.json，也可以新增小型 provenance JSON/CSV，但 runtime_gap_closure_table.csv 的 cache_provenance_isolation artifact_path 必须指向包含完整字段的 artifact。该 artifact 至少要显式包含：

checkpoint_path
optimizer_steps
encoder_profile
encoder_scale_channels 或等价 strong encoder channel profile
prototype_source
prototype_summary_path
selected_case_ids
eval_case_ids
patch_shape
mode/smoke_scope
commands_run 或 commands_run_path
artifact paths for the required CSV outputs

必须加严 scripts/evaluation/export_srr_v3_m2_runtime_repair_smoke.py 的 strict validator：如果 provenance artifact 缺少上述字段、字段为空、checkpoint_path/optimizer_steps 未明确说明 no-training smoke 状态、selected_case_ids 为空、eval_case_ids 为空、或 cache_provenance_isolation 指向的 artifact 不存在/不含完整 provenance，则 strict validation 必须失败。known-bad validator smoke 也必须覆盖 claim-only 或 missing-provenance packet 并 fail closed。

完成后更新 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/ 中相关轻量文件：runtime_smoke_summary.json 或新增 provenance artifact、runtime_gap_closure_table.csv、unit_test_report.md、commands_run.md、result.md、completion_check.md、review_request.md、MANIFEST.md；如修改了 helper/validator，也提交对应小型 first-party source。completion_check.md 只能在 provenance 字段完整、strict validator 通过、known-bad validator fail closed、且没有新增 M2 scope violation 时写 M2_READY_FOR_REVIEW；否则写 M2_NEEDS_REVISION 或 M2_NEEDS_EVIDENCE。

完成后用 git add -f 提交 M2 continued packet 供后续 GPT/独立 reviewer 审阅所需的全部轻量文件和必要 helper/source/config；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets、environment dumps 或整个 runtime result tree；不要 push，由用户手动 push。不要写 review.md，不要批准自己，不要启动 M3。M2 最终是否给 M2_AUDITED_GO 由后续 GPT/独立 reviewer 决定。
```

## M3 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md。开始前必须确认 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md 存在且包含 M2_AUDITED_GO，否则停止。这是最小有效 pilot，不是 full fold、不是 challenge candidate。必须满足 minimum_effective_training：至少 1200 optimizer steps、1800 秒 train loop、12 个 eval cases、one-batch overfit、prediction sanity、loss decrease、same-split nnU-Net baseline、cache isolation。必须输出 gate/residual stats、prototype bank summary、same-split help/harm、hard subgroup metrics、adequacy_check、completion_check.md、review_request.md 和 MANIFEST.md。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M4。
```

## M4 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md。开始前必须确认 results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md 存在且包含 M3_AUDITED_GO，否则停止。目标是解释 SRR-v3 机制的 help/harm，而不是训练 full folds。围绕 closed gate、no anchor、residual frozen、dictionary/prototypes、semantic retrieval、component proposal、anatomy ROI、local refinement 做 bounded ablation；每行必须报告 same-split nnU-Net help/harm、gate/residual、prototype/dictionary、proposal/refinement、hard subgroup 和 provenance。结果写入 results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md。
```

## M5 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md。开始前必须确认 results/20260705_srr_v3_m0_architecture_master_contract/review.md 存在且包含 M0_AUDITED_GO，否则停止。Cine 是副线，不阻塞 MyoPS。目标是审计和补足 Cine secondary diagnostic evidence：CineMA/anatomy prior、ANTsPy SyN same-safe-subset matrix、VoxelMorph trained/usable status、frame0/ED controls、temporal dictionary readiness、frame-quality/motion-saliency router。不能把 frame0-only、one-case SyN smoke、untrained VoxelMorph adapter 冒充 full temporal retrieval。结果写入 results/20260705_srr_v3_m5_cine_secondary_contract/。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md。
```

## M6 executor: concrete SRR-v3 MyoPS architecture/runtime repair

```text
只执行 M6：concrete SRR-v3 MyoPS architecture/runtime repair。开始前必须确认：

- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` 存在且包含 `M4_AUDITED_GO`；
- M6 不依赖 M5；M5 是 Cine 副线诊断，不是 MyoPS M6 的前置条件；
- 不允许 full fold training；不允许 validation packaging/upload；不允许 route promotion；不允许 hosted metric claim；不允许启动 M7；
- 必须提交 lightweight evidence packet 供独立 reviewer 审阅；不要 push。

如果 M4 prerequisite 不满足，停止并写 `M6_BLOCKED_BY_M4`，不得做科学任务。

图像读取与证据边界：当前仓库规则要求 SRR-v2、SRR-v2.5、SRR-v3 以及后续版本的架构图必须通过 ChatGPT Project background materials 或当前对话上传图片进行视觉读取；GitHub connector 暴露的 PNG blob、SHA、base64 metadata、文件名或旧总结都不能替代视觉读取。本 M6 prompt 是基于仓库中可读、可审计的文本、源码、M0-M4 review 和 shared design addendum 合并出的具体执行合同；executor 不得声称自己已经完成 `visual_read_status: READ_FROM_PROJECT_BACKGROUND`，除非当前线程实际具备并读取了 Project background 或当前对话图片。

M6 的任务不是“再训练一下 M3”，也不是“把 SRR 变成 nnU-Net 后处理”。M6 必须把当前 SRR-v3 MyoPS path 修成一个可以进入 M7 最小有效训练的 architecture/runtime 系统。它必须同时满足：

- SRR retrieval/proposal/refiner/arbitration 在 forward 中实际被调用；
- loss components 不是空日志，而是有数值、梯度或 one-step update evidence；
- nnU-Net 作为 segmentation context/evidence/safety fallback，不是唯一最终答案；
- closed/fallback path 必须精确复现 nnU-Net；
- SRR 在 correction-positive synthetic/real smoke 中必须能产生非零贡献；
- no-T2 edema 在 proposal、refiner、loss、decode、export 全链路安全。

M6 必须首先写出 code-gap map，不得直接跑旧代码导表。code-gap map 写入 `code_diff_summary.md` 与 `architecture_component_trace.csv`，逐项列出当前 first-party code 到目标实现的差距、修复状态、证据路径和仍未关闭的 blocker。至少要检查并修复 encoder profile、pair-specific dictionary config、prototype loading/source checks、segmentation context interface、pathology-specific proposal、bounded soft-ROI refiner、explicit arbitration、expanded total loss 和 strict validator。只生成 CSV/Markdown 而没有对应 first-party code 改动或明确 blocker，不能写 ready。

Codex 不能自己设计 variant。M6 必须实现或明确保留以下三个 variant；如果某个 variant 由于真实 blocker 无法实现，必须写清 blocker，不得悄悄省略。

1. `m6_full_srr_context_arbitration`
   - encoder profile: 默认 `balanced_4scale`，channels `16/32/64/128`；另做 `full_4scale` `32/64/128/256` 的 forward/memory smoke；
   - dictionary: `dict_full_interaction`，每尺度 shared 8、LGE-private 4、C0-private 4、T2-private 4、LGE-T2 interaction 4、LGE-C0 interaction 4、T2-C0 interaction 4；
   - prototype: scar-positive、scar-safe-negative、edema-positive、edema-safe-negative 四组；edema-positive 和 edema-safe-negative 只能来自 T2-present 安全证据；
   - proposal: scar/edema separate proposal decoder，`positive_similarity - negative_similarity + anchor_component + anatomy_distance + uncertainty + learned_residual`；
   - refiner: scar small-ROI crop refiner、edema context-ROI crop refiner；
   - arbitration: learnable or rule-initialized branch/evidence arbitration，输出 per-case/per-class weights。

2. `m6_conservative_component_arbitration`
   - encoder profile: `safe_4scale` 或 `balanced_4scale`；
   - dictionary: `dict_conservative_private_shared`，shared 6、LGE-private 4、C0-private 2、T2-private 4，可选 LGE-T2 interaction 2；
   - proposal: 强依赖 nnU-Net components 和 uncertainty，只允许 bounded correction；
   - refiner: scar 更高 precision，edema no-T2 更强关闭；
   - arbitration: component-level 或 class-level conservative rule，只有在 SRR evidence 高于阈值且 anchor uncertainty 高时打开。

3. `m6_scar_precision_edema_safe`
   - scar 分支偏向 LGE-private、LGE-C0/LGE-T2 interaction、small ROI、remote-FP suppression；
   - edema 分支偏向 T2-private、T2 interaction、larger context ROI、T2-present-only learning；
   - no-T2 case 中 edema proposal/refiner/final decode/export 全部 inert；
   - scar 不得因 edema safety 改动而退化为全空或大面积 FP。

M6 必须把 encoder/decoder 容量写死为可审计 profile，而不是继续让 Codex 用 tiny 结构偷懒。必需 profile：

- `full_4scale`: `32/64/128/256`，至少跑 synthetic 或 one real patch forward；如果 OOM，要记录 exact command、patch shape、error、memory context；
- `balanced_4scale`: `16/32/64/128`，默认 M7 候选；
- `safe_4scale`: `12/24/48/96` 或 `8/16/32/64`，只作为 OOM fallback 或 smoke，不得无理由作为最终设计。

不得继续以 `tiny_3scale`、`base_channels=10` 或旧 `strong_4scale` 名称糊弄。每个 profile 必须导出：input shape、availability pattern、encoder scale shapes、decoder scale shapes、parameter count、activation/memory estimate、runtime seconds。decoder 必须是 anatomy/scar/edema task-specific decoder，不能把所有任务压成一个 shallow shared head。

Dictionary 必须实现 pair-specific config，而不是只复用旧 `interaction_slots` 默认值。`dict_full_interaction`、`dict_conservative_private_shared` 和 `m6_scar_precision_edema_safe` 的 task-specific router bias 都必须在代码/config 中可审计。无对应 modality 时 private/interaction slot 必须 mask；no-T2 case 中 T2-private 与含 T2 interaction slot 不得作为 edema evidence。`retrieval_bank_runtime_sanity.csv` 必须证明这些 mask 和 usage 规则。

Prototype bank 不得使用 deterministic placeholder 作为 ready evidence。允许 deterministic prototype 仅用于 synthetic smoke 或 known-bad validator，但 `M6_READY_FOR_REVIEW` 必须有 real train/OOF 或可审计 anchor-derived prototype source。若任一 edema bank 为空，或 no-T2 myocardium 进入 edema negative，必须写 `M6_NEEDS_EVIDENCE` 或 `M6_NEEDS_REVISION`。

M6 必须新增或明确修复 `segmentation_context_interface`，使 nnU-Net/强分割模型作为 evidence 进入 SRR，而不是绕过 SRR。输入字段至少包括：

- `anchor_probabilities` 或 `anchor_logits`；
- `anchor_hard_prediction`；
- `scar_component_mask`、`edema_component_mask`；
- `anchor_entropy`、`anchor_margin`、`anchor_confidence`；
- `component_size`、`component_distance_to_union`、`remote_component_flag`；
- `anatomy_union_support` 或从 anchor/anatomy decoder 派生的 union/LV/RV context。

必须导出 `segmentation_context_interface_sanity.csv`，每行包含 case_id、class、anchor source path、tensor shapes、nonzero rates、component counts、uncertainty statistics、used_by_proposal、used_by_refiner、used_by_arbitration。

M6 必须导出 `retrieval_bank_runtime_sanity.csv`，至少包含：variant、case_id、availability pattern、scale、task、group、slot_count、active_slot_count、mean_usage、entropy、max_weight、collapse_warning、masked_invalid_slot_usage、t2_private_usage_when_no_t2、gradient_norm 或 one-step update status。

M6 必须导出 `prototype_bank_runtime_sanity.csv`，至少包含：variant、bank_type: scar_positive / scar_safe_negative / edema_positive / edema_safe_negative、source split、source cases、component count、voxel count、feature stage、prototype count、no_t2_used_as_edema_negative: 必须为 false、leakage_check、empty_bank_status。如果 edema-positive 或 edema-safe-negative 为空，M6 不能写 ready。

M6 必须导出 `anatomy_proposal_sanity.csv` 和 `refiner_roi_component_sanity.csv`。

`anatomy_proposal_sanity.csv` 至少包含：`P_union/P_LV/P_RV` nonzero rate、distance/proximity map range、uncertainty range、scar proposal foreground rate、edema proposal foreground rate、positive/negative similarity means、anchor component evidence contribution、proposal recall/precision proxy、outside-myocardium FP proxy、no-T2 edema proposal voxels（必须为 0）。

Proposal 必须显式实现 pathology-specific 公式，不得退化为一层 dense head。对 `k in {scar, edema}`，proposal logit 至少包含：

`ell_k = w_pos_k * s_pos_k - w_neg_k * s_neg_k + w_anatomy_k * A_k + w_context_k * C_k + w_uncertainty_k * U_k + r_k`

其中 `s_pos_k` 是 positive prototype similarity，`s_neg_k` 是 safe-negative / hard-negative similarity，`A_k` 是 anatomy/distance prior，`C_k` 是 nnU-Net component/context evidence，`U_k` 是 uncertainty，`r_k` 是 learned residual。Scar 必须 LGE-dominant；edema 必须 T2-conditioned；no-T2 edema proposal 必须为 0 或 logits 强关闭。

`refiner_roi_component_sanity.csv` 至少包含：refiner type: scar_small_roi / edema_context_roi、crop bounds、crop_volume_ratio、crop_mask_volume_ratio、`is_full_volume_crop`（必须为 false）、original modality crop used: scar 必须 LGE，edema 必须 T2-present only、anchor/prototype/dictionary/anatomy/uncertainty inputs used、residual magnitude、bounded_delta max、component_count_delta proxy、remote_FP_delta proxy、no-T2 edema final voxels（必须为 0）。

M6 必须实现 explicit arbitration。每个 case/class 至少输出：`segmentation_weight`、`srr_retrieval_weight`、`proposal_weight`、`refiner_weight`、`chosen_source`、`fallback_reason`、`anchor_confidence`、`srr_confidence`、`correction_mask_rate`、`label_delta_vs_anchor`。

必须有两个 sanity：

1. correction-positive sanity：在 synthetic known-error 或 explicit high-uncertainty real patch 中，SRR/proposal/refiner contribution 必须非零；
2. low-quality SRR sanity：当 SRR evidence 被置空、prototype bank 为空或 proposal confidence 低时，arbitration 必须选择 segmentation branch，final labels 必须精确等于 anchor。

`decode_gate_consistency_sanity.csv` 必须证明：当 explicit fallback、closed gate 或 refiner mask 关闭时，final labels 与 segmentation branch 完全一致。若出现 hidden decode delta，strict validator 必须失败。

M6 必须新增或改造 loss，使 `loss_refiner_component_sanity.csv` 至少覆盖以下组件：

- `loss_anatomy_union_lv_rv`；
- `loss_scar_proposal`；
- `loss_edema_proposal_t2_present_only`；
- `loss_scar_refiner_roi`；
- `loss_edema_refiner_t2_present_roi`；
- `loss_anchor_preservation_outside_roi`；
- `loss_branch_arbitration_consistency`；
- `loss_bounded_correction`；
- `loss_component_remote_fp`；
- `loss_no_t2_edema_safety`；
- `loss_dictionary_entropy_coverage_load_balance`；
- `loss_prototype_diversity_margin`。

这些 loss component 必须进入实际 total loss，不得只写日志。Canonical total loss 至少包含：

`L_total = lambda_ana * L_ana + lambda_scar_prop * L_scar_prop + m_T2 * lambda_edema_prop * L_edema_prop + lambda_scar_ref * L_scar_ref + m_T2 * lambda_edema_ref * L_edema_ref + lambda_anchor * L_anchor + lambda_arb * L_arb + lambda_delta * L_bounded + lambda_neg * L_neg + lambda_noT2 * L_noT2 + lambda_dict * L_dict + lambda_proto * L_proto`

也就是说，至少包含 anatomy、scar proposal、T2-present edema proposal、scar refiner、T2-present edema refiner、anchor preservation、arbitration consistency、bounded correction、negative/hard-negative、no-T2 safety、dictionary regularization 和 prototype regularization。每个 non-N/A component 必须有 positive weight、nonzero or justified zero、requires_grad、gradient_norm 或 synthetic backward/one-step update evidence。不能只有自然语言说明。M7 必须用同一套 expanded loss 训练，不能 M6 只做 synthetic backward、M7 又退回旧 `srr_total_loss()`。

M6 必须新增或加严 strict validator，使以下 known-bad packet fail closed：

- claim-only architecture trace；
- missing `srr_v3_fidelity_contract.md`；
- dictionary slot usage 全空；
- prototype bank 空或 no-T2 myocardium 被当作 edema negative；
- segmentation context 直接绕过 SRR 成为 final output 且无 explicit fallback reason；
- closed/fallback gate 下 final labels 仍改变；
- refiner 是 full-volume residual；
- loss components 为空或无 backward evidence；
- SRR contribution 在 correction-positive sanity 中全为 0；
- no-T2 edema 在 proposal/refiner/final decode/export 任一环节非零。

M6 结果写入 `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`，必须写齐：

- `result.md`
- `srr_v3_fidelity_contract.md`
- `architecture_component_trace.csv`
- `m4_failure_mapping.csv`
- `code_diff_summary.md`
- `encoder_decoder_capacity_sanity.csv`
- `segmentation_context_interface_sanity.csv`
- `retrieval_bank_runtime_sanity.csv`
- `prototype_bank_runtime_sanity.csv`
- `anatomy_proposal_sanity.csv`
- `branch_arbitration_sanity.csv`
- `decode_gate_consistency_sanity.csv`
- `loss_refiner_component_sanity.csv`
- `refiner_roi_component_sanity.csv`
- `no_t2_safety_sanity.csv`
- `strict_validator_report.md`
- `unit_test_report.md`
- `commands_run.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

`completion_check.md` 只能写：

- `M6_READY_FOR_REVIEW`
- `M6_NEEDS_REVISION`
- `M6_NEEDS_EVIDENCE`
- `M6_BLOCKED_BY_M4`

不能写 `M6_READY_FOR_REVIEW` 的情况：

- 没有逐项 architecture trace；
- 没有先写 code-gap map，或 code-gap map 只列 claim 没有 first-party code path / runtime artifact / blocker；
- 使用 tiny three-scale 结构作为唯一证据；
- 只复用旧 `interaction_slots` / deterministic placeholder prototype / 旧 baseline residual gate 当作通过证据；
- dictionary/prototype/proposal/refiner/loss/arbitration 任一核心模块没有 runtime evidence；
- no-T2 edema 不安全；
- local refiner 是 full-volume；
- closed/fallback 下 final labels 改变；
- SRR contribution 在 correction-positive sanity 中为 0；
- loss components 没有数值/梯度/one-step sanity；
- strict validator 不能 fail closed known-bad packets；
- reviewer 需要的轻量证据没有 git-tracked。

完成后必须 `git add -f` 并本地 commit M6 轻量证据和必要 first-party helper/source/config；不要提交 checkpoint、NIfTI、upload package、大日志、raw data、secrets、environment dump 或整棵 runtime tree；不要 push；不要写 `review.md`；不要启动 M7。
```

## M6 executor (continued): reviewer-blocker repair

```text
只继续执行 M6，不是 M7。开始前必须确认：

- `results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md` 存在且包含 `M4_AUDITED_GO`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_NEEDS_REVISION`；
- 当前任务只修复 M6 review 指出的 blocker，不允许 full fold training、validation packaging/upload、route promotion、hosted metric claim、scientific stop 或启动 M7；
- 完成后必须提交 lightweight evidence packet 供独立 reviewer 重新审阅；不要 push。

本 continued 任务不是重新设计 SRR-v3，也不是用更多自然语言解释原 M6。只允许围绕 M6 review 的四个 blocker 做最小必要 first-party code/helper/test/result 修复：

1. 补齐 low-quality SRR branch arbitration sanity。
   - `branch_arbitration_sanity.csv` 必须同时包含 correction-positive sanity 和 low-quality SRR/prototype/proposal sanity；
   - low-quality sanity 必须构造 SRR evidence 被置空、prototype bank 为空或 proposal confidence 低的 case；
   - 该 case 必须让 arbitration 选择 segmentation branch；
   - final labels 必须逐 voxel 精确等于 segmentation/anchor branch；
   - 必须导出明确字段：`sanity_type`、`chosen_source`、`fallback_reason`、`anchor_confidence`、`srr_confidence`、`correction_mask_rate`、`label_delta_vs_anchor`、`final_equals_anchor_labels` 或等价可审计字段；
   - 不能把 `decode_gate_consistency_sanity.csv` 的 explicit fallback identity 当作替代证据。

2. 把 strict validator 改成真实 fail-closed validator 或等价 command-driven known-bad 检查。
   - 必须构造并验证 M6 prompt 中列出的 known-bad packets，至少覆盖：claim-only architecture trace、missing fidelity contract、dictionary slot usage 全空、prototype bank 空或 no-T2 myocardium 被当作 edema negative、segmentation context 直接绕过 SRR 且无 explicit fallback reason、closed/fallback gate 下 final labels 改变、full-volume refiner、loss components 为空或无 backward evidence、correction-positive sanity 中 SRR contribution 全 0、no-T2 edema 在 proposal/refiner/final decode/export 任一环节非零；
   - `strict_validator_report.md` 必须记录每个 known-bad packet 的名称、命令或 validator entrypoint、expected failure、actual exit code、failure reason；
   - actual exit code 必须是非零或等价 fail status，不能只从 in-memory good packet 推导 `PASS_FAIL_CLOSED`；
   - 如果某个 known-bad case 因真实技术 blocker 无法实现，必须写 `M6_NEEDS_REVISION`，不能写 ready。

3. 修正 readiness/status 边界。
   - `result.md`、`completion_check.md`、`review_request.md`、`srr_v3_fidelity_contract.md` 必须明确区分 synthetic anchor-derived smoke、real train/OOF evidence、real-case runtime evidence；
   - 如果 continued packet 仍然只有 synthetic anchor-derived smoke，则不得声称 train/OOF prototype readiness、M7 training readiness 已完全证明，除非 prompt 中的 M6 gate 被真实满足且证据文件清楚限定为 architecture/runtime smoke；
   - 不得把 18 分钟或短 runtime 本身作为成功证据；必须靠 hard-gate evidence 通过。

4. 新增或补足 unit tests 覆盖 M6 hard gates。
   - 测试必须覆盖 low-quality SRR arbitration 选择 segmentation branch 且 final labels 等于 anchor；
   - 测试必须覆盖 strict validator 对至少两个 known-bad packet 返回 fail-closed，其中一个必须是 hidden decode delta 或 no-T2 edema unsafe，另一个必须是 missing/claim-only evidence 或 zero SRR contribution；
   - `unit_test_report.md` 必须记录 exact test command、exit code、测试模块/用例名和结果；
   - 仅 py_compile 或旧 unittest 通过不算满足 continued blocker。

允许修改 `scripts/evaluation/run_srr_v3_m6_concrete_architecture_repair.py`、M6 strict validator/helper、M6 相关 first-party model/loss/runtime 代码和聚焦 unit tests；不要做无关重构。可以重新生成 M6 result 目录中的轻量 Markdown/CSV/JSON 证据。必须保留或更新 `MANIFEST.md`，列出 revised evidence 和必要 first-party code/test 文件。

M6 continued 结果仍写入：

`results/20260705_srr_v3_m6_myops_concrete_architecture_repair/`

必须至少更新：

- `result.md`
- `branch_arbitration_sanity.csv`
- `strict_validator_report.md`
- `unit_test_report.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

如 readiness 边界或 generator/helper 发生变化，也必须同步更新相关 evidence：

- `srr_v3_fidelity_contract.md`
- `code_diff_summary.md`
- `architecture_component_trace.csv`
- `commands_run.md`
- 相关 first-party helper/source/test files

`completion_check.md` 只能写：

- `M6_READY_FOR_REVIEW`
- `M6_NEEDS_REVISION`
- `M6_NEEDS_EVIDENCE`
- `M6_BLOCKED_BY_M4`

只有在 low-quality SRR arbitration、真实 fail-closed known-bad validator、readiness/status 边界和 hard-gate unit tests 全部有可审计证据时，才能写 `M6_READY_FOR_REVIEW`。如果任一 blocker 未关闭，必须写 `M6_NEEDS_REVISION` 或 `M6_NEEDS_EVIDENCE` 并停止。

完成后必须 `git add -f` 并本地 commit M6 continued 轻量证据和必要 first-party helper/source/test/config；不要提交 checkpoint、NIfTI、upload package、大日志、raw data、secrets、environment dump 或整棵 runtime tree；不要 push；不要写 `review.md`；不要批准自己；不要启动 M7。
```

## M7 executor: concrete MyoPS training and CineMA/Cine diagnostic utilization

```text
只执行 M7：concrete MyoPS training and CineMA/Cine diagnostic utilization。M7 只能在 M6 独立审阅通过后启动。必须确认：

- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`；
- 如果 M7 中启用 Cine 子线，还必须确认 `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 包含 `M5_AUDITED_DIAGNOSTIC_GO`；
- M7 仍不是 route promotion、不是 validation packaging/upload、不是 hosted metric claim；
- M7 必须停止在 executor result + completion_check + review_request，不得写 `review.md`，不得启动后续 milestone。

如果 M6 未通过，写 `M7_BLOCKED_BY_M6` 并停止。Cine 子线若 M5 未通过，可以只阻塞 Cine 子线，不应阻塞 MyoPS M7 训练；但必须写清 `CINE_BLOCKED_BY_M5`。

M7 是第一个允许训练 M6 修复后 concrete variants 的 milestone。它的目标不是把结果包装成 challenge candidate，而是判断 M6 修复后的 SRR-v3 是否在最小有效训练下产生可靠、可解释、可审计的 help/harm 证据，并且判断 CineMA/registration/temporal evidence 是否已经从 M5 的 diagnostic gap 走向可用的 Cine secondary diagnostic path。

M7 必须回答四个问题：

1. M6 的三个 concrete variants 在足够训练后是否有任一 variant 相对同 split nnU-Net 改善或至少不伤害关键 metric？
2. 改善或伤害来自哪里：dictionary、prototype、proposal、refiner、arbitration、loss 还是 no-T2 safety？
3. 训练是否稳定：loss 是否下降并 plateau，validation 是否稳定，不是几分钟结束的假证据？
4. CineMA 是否真正被用作 Cine anatomy/frame-quality/registration/temporal-dictionary evidence，而不是只作为 frame0 control 或文字状态？

M7 必须训练并评估下列 variants，除非 M6 review 明确禁止某个 variant。Codex 不能自行缩减 matrix；如资源不足，必须按顺序训练并记录 blocker。

1. `m7_full_srr_context_arbitration`：来自 M6 的 `m6_full_srr_context_arbitration`。默认 encoder 为 `balanced_4scale` `16/32/64/128`。如果 `full_4scale` `32/64/128/256` 在 M6 smoke 中可运行，允许作为额外 high-capacity variant，但不能替代 balanced 默认。
2. `m7_conservative_component_arbitration`：来自 M6 的 `m6_conservative_component_arbitration`。它是安全/稳定对照，目标是减少 remote FP、HD95 和 component explosion。
3. `m7_scar_precision_edema_safe`：来自 M6 的 `m6_scar_precision_edema_safe`。它必须报告 scar 和 edema 分支的不同 loss、ROI、proposal、arbitration 行为，不能只给总 Dice。

只有当前三项主 variant 至少完成 one-batch overfit 与 baseline sanity 后，才允许新增最多两个 ablation：

- `no_interaction_dictionary`：去掉 interaction slots；
- `frozen_prototype_bank`：prototype 固定，仅训练 proposal/refiner/arbitration。

不得跑大规模 temperature/threshold grid。阈值、温度、gate bias 只能在预先记录的有限集合中选择，且不能用 validation GT 做 case-id tuning。

M7 必须按 shared 的三个 required variants 训练。不得把未跑 variant 当作 skipped success；资源不足时只能按顺序记录 blocker。M7 必须使用 M6 expanded total loss 和 concrete architecture/runtime repairs，不能退回旧 `srr_total_loss()` 或旧 SRR baseline path。

M7 不要求超过 8 小时，但必须避免几分钟结束的训练假证据。每个 MyoPS variant 必须满足以下条件之一：

- `optimizer_steps >= 3000` 且 `train_loop_seconds >= 1800`；或
- 明确达到 plateau：最近 5 个 validation events 中 primary composite objective 相对改善 `< 1%`，且各核心 loss component 没有单项爆炸；或
- 因 scheduler/OOM/bug 中止，并写 `M7_NEEDS_REVISION` 或 `M7_NEEDS_EVIDENCE`，不得写成功或失败。

推荐训练目标：

- `optimizer_steps`: `6000-12000`；
- validation interval: 每 `300-500` steps；
- eval cases: 至少 `12` 个固定 case，优先 `20` 个；
- hard subgroups: all-case、T2-present、GT-positive、no-T2 empty-GT、CenterB/CenterC、remote-FP-positive、small-lesion、large-lesion；
- one-batch overfit: 每个 variant 必须 pass；
- loss decrease: total loss 与关键 loss component 均需报告，不只总 loss。

如果训练不足 1800 秒且没有 plateau，`experiment_adequacy_decision` 必须是 `FAIL` 或 `PARTIAL`，`scientific_resolution_status` 必须是 `SCIENTIFIC_UNDERTRAINED` 或 `SCIENTIFIC_NEEDS_EVIDENCE`。不得把 undertrained run 写成 route failure 或 route promotion。

M7 必须用同 split nnU-Net 作为 reference，不能只和旧 SRR 比。每个 variant 必须报告：scar Dice、HD95、component count、remote FP、volume ratio；edema all-case Dice/HD95；edema T2-present/complete Dice/HD95；edema GT-positive Dice/HD95；no-T2 empty-GT edema stability；CenterB/CenterC 指标；per-case help/harm；branch arbitration chosen_source 分布；dictionary/prototype usage；proposal recall/precision proxy；refiner crop/residual statistics；label/export caveat。

Best variant selection 不是 Codex 主观判断，必须按下列规则：

1. 任何 no-T2 edema unsafe 的 variant 直接 `REJECT`；
2. 任何 scar 相比 nnU-Net 明显退化且没有 edema 大幅收益的 variant 直接 `REJECT`；
3. 首先看 primary target：`myops_scar` 与 `myops_edema` 的同 split help/harm；
4. 若 Dice 接近，优先 HD95、component_count、remote_FP 更好者；
5. 若 MyoPS 没有任何 variant 同时满足 no-T2 safety、scar non-regression 和 edema hard-subgroup improvement，则写 `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`，不得包装为成功；
6. 只有在至少一个 primary 或 critical secondary metric 明确改善，且无 catastrophic regression，且 M7 review 支持时，后续 GPT 才能考虑下一 milestone；M7 executor 本身不许 route promotion。

M7 必须按 step 导出 loss component 曲线，至少包含：anatomy union/LV/RV、scar proposal、edema proposal T2-present、scar refiner ROI、edema refiner ROI、anchor preservation、branch arbitration consistency、bounded correction、component/remote-FP、no-T2 edema safety、dictionary entropy/coverage/load-balance、semantic family/interaction mass、prototype diversity/margin。

必须输出 `loss_component_by_step.csv` 与 `loss_component_gradient_sanity.csv`。如果某个 loss component 长期为 0，必须解释它是合法不适用还是 bug；无解释的空 loss component 是 reviewer blocker。

M5 已经说明 CineMA/anatomy prior 目前只是部分支持，不能当成 registration 或 temporal retrieval completion。M7 若启用 Cine 子线，必须把 CineMA 用成以下三类 evidence，而不是只写“尝试过”：

1. CineMA anatomy prior：对 same-safe-subset 的 cine frames 运行或读取 CineMA/equivalent anatomy output，记录 source path、version、weights/source status、input preprocessing、frame selection、class mapping、output label/probability shape、myocardium/anatomy Dice/HD95 against available local reference 或 frame0 control、whether anatomy-only or pathology-capable。CineMA 输出不能直接当 pathology prediction。
2. CineMA-assisted registration：构建 same-safe-subset matrix，至少包含 frame0/ED identity control、CineMA frame-wise anatomy prior control、CineMA + ANTsPy SyN、CineMA + SimpleITK Demons/B-spline fallback、optical-flow/feature-warp proxy（必须标为 descriptor/proxy）、VoxelMorph（如果没有训练或可审计 weights，必须标 `UNTRAINED_NOT_USABLE`，不能进 usable registration）。每行必须报告 same case/frame、before/after anatomy Dice/HD95、Jacobian/fold proxy、round-trip/inverse consistency proxy、runtime、failure reason。one-case SyN smoke 不能作为 full registration matrix。
3. Cine temporal dictionary：如果 registration matrix 至少有一个非-reference option 合格，才允许构建 temporal dictionary。temporal dictionary 必须包括 ED/reference anchor features、selected non-reference frame features、warped or descriptor features、frame-quality score、motion-saliency score、temporal representer slot usage、temporal aggregation output、local class_1 myocardium proxy and class_3 sanity、hosted metric caveat。如果 registration matrix 不合格，必须写 `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`，不得用 frame0-only 代替 temporal retrieval。

若已有 CineMA output 可用却未使用，写 `M7_NEEDS_EVIDENCE`；若缺权重、缺输出或合规不明，写 `cinema_blocker_report.md` 并说明 exact blocker。Frame0-only、one-case SyN smoke、untrained VoxelMorph、optical-flow descriptor 都不得冒充 completed registration or temporal retrieval。

Cine 是 secondary diagnostic，不得阻塞 MyoPS 主线训练。M7 可以把 Cine 子线作为同一 milestone 的 secondary packet，但必须分开写 MyoPS 与 Cine 的 decision：

- `myops_decision`: variant improvement / no promotion / needs revision / undertrained；
- `cine_decision`: CineMA used / registration gap remains / temporal dictionary ready or blocked；
- `combined_decision`: 不得把 Cine diagnostic success 当成 MyoPS promotion，也不得把 MyoPS failure 当成 Cine stop。

M7 结果写入 `results/20260705_srr_v3_m7_training_and_cine_utilization/`，必须写齐：

- `result.md`
- `m7_execution_plan.md`
- `variant_matrix.csv`
- `training_adequacy_by_variant.csv`
- `one_batch_overfit_by_variant.csv`
- `training_curve_by_variant.csv`
- `validation_curve_by_variant.csv`
- `loss_component_by_step.csv`
- `loss_component_gradient_sanity.csv`
- `prediction_sanity_by_variant.csv`
- `same_split_help_harm.csv`
- `hard_subgroup_metrics.csv`
- `branch_arbitration_by_case.csv`
- `dictionary_prototype_usage_by_variant.csv`
- `proposal_refiner_by_case.csv`
- `no_t2_safety_by_variant.csv`
- `best_variant_decision.md`
- `failure_interpretation.md`
- `cinema_usage_report.md` if Cine subline runs, otherwise `cinema_blocker_report.md`
- `registration_same_subset_matrix.csv` if Cine subline runs
- `temporal_dictionary_evidence.csv` if temporal dictionary is attempted
- `cine_metrics_summary.csv` if Cine metrics are computed
- `label_export_qc.md`
- `commands_run.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

`completion_check.md` 只能写：

- `M7_READY_FOR_REVIEW`
- `M7_NEEDS_REVISION`
- `M7_NEEDS_EVIDENCE`
- `M7_NEEDS_MONITOR`
- `M7_BLOCKED_BY_M6`

不能写 `M7_READY_FOR_REVIEW` 的情况：

- 任一必跑 MyoPS variant 没有训练且没有 blocker；
- required variant 被自行缩减、未跑 variant 被当作 skipped success，或 M7 退回旧 loss/model path；
- 训练不足 1800 秒且没有 plateau；
- 没有 same-split nnU-Net help/harm；
- 没有 loss component 曲线；
- 没有 hard subgroup metrics；
- no-T2 edema unsafe；
- best variant decision 由自然语言主观判断而非 metric table 决定；
- Cine 子线声称使用 CineMA 但没有 class mapping/output path/metric 或 blocker；
- registration 被 one-case SyN/untrained VoxelMorph/frame0-only 冒充完成；
- temporal dictionary 在 registration gap 下仍被写成 ready；
- reviewer 所需轻量证据没有 git-tracked。

完成后必须 `git add -f` 并本地 commit M7 轻量证据和必要 first-party helper/source/config；不要提交 checkpoint、NIfTI、upload package、大日志、raw data、secrets、environment dump 或整棵 runtime tree；不要 push；不要写 `review.md`；不要启动后续 milestone。

开始前必须确认：

1. `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`。如果没有，写 `M7_BLOCKED_BY_M6` 并停止。
2. 如果启用 Cine 子线，必须确认 `results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 包含 `M5_AUDITED_DIAGNOSTIC_GO`。如果没有，只阻塞 Cine 子线，写清 `CINE_BLOCKED_BY_M5`，不得阻塞 MyoPS M7 训练。
3. M6 只证明 architecture/runtime smoke，不是 train/OOF prototype readiness、real-case runtime proof 或 M7 training evidence。M7 必须重新训练并评估，不得复用 M6 synthetic tensors 作为训练或性能证据。

M7 必须训练并评估 shared M7 规定的三个 required variants，除非 M6 review 明确禁止某个 variant：

1. `m7_full_srr_context_arbitration`
2. `m7_conservative_component_arbitration`
3. `m7_scar_precision_edema_safe`

不得自行缩减 matrix；不得把未跑 variant 写成 skipped success；不得退回旧 `srr_total_loss()`、旧 SRR baseline path、旧 `tiny_3scale` shortcut 或 M6 synthetic-only generator。M7 必须使用 M6 修复后的 concrete architecture/runtime path、expanded total loss、branch arbitration、segmentation context interface、dictionary/prototype/proposal/refiner/no-T2 safety wiring。

每个 required MyoPS variant 必须先做 one-batch overfit；one-batch 失败时写 `M7_NEEDS_REVISION` 或 `M7_NEEDS_EVIDENCE`，不得继续把失败 variant 当作训练充分。正式训练每个 variant 必须满足以下之一：

- `optimizer_steps >= 3000` 且 `train_loop_seconds >= 1800`；
- 或最近 5 个 validation events 显示 primary composite objective 相对改善 `< 1%`，且核心 loss component 没有单项爆炸；
- 或因 scheduler/OOM/bug 中止，并明确写 `M7_NEEDS_REVISION` / `M7_NEEDS_EVIDENCE` / `M7_NEEDS_MONITOR`，不得写成功或失败结论。

推荐目标为 `6000-12000` optimizer steps，validation interval 每 `300-500` steps，至少 12 个固定 eval cases，优先 20 个。hard subgroup 至少覆盖 all-case、T2-present、GT-positive、no-T2 empty-GT、CenterB/CenterC、remote-FP-positive、small-lesion、large-lesion。

M7 必须用 same-split nnU-Net 作为唯一主 baseline reference，不能只和旧 SRR 比。每个 variant 必须报告：

- scar Dice、HD95、component count、remote FP、volume ratio；
- edema all-case Dice/HD95；
- edema T2-present/complete Dice/HD95；
- edema GT-positive Dice/HD95；
- no-T2 empty-GT edema stability；
- CenterB/CenterC 指标；
- per-case help/harm；
- branch arbitration chosen_source 分布；
- dictionary/prototype usage；
- proposal recall/precision proxy；
- refiner crop/residual statistics；
- label/export caveat。

best variant decision 必须由 metric table 决定，不得自然语言主观选择。任何 no-T2 edema unsafe 的 variant 直接 `REJECT`。任何 scar 相比 nnU-Net 明显退化且没有 edema 大幅收益的 variant 直接 `REJECT`。若没有任何 variant 同时满足 no-T2 safety、scar non-regression 和 edema hard-subgroup improvement，写 `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`，不得包装为成功。

必须按 step 导出 loss component 曲线，至少包含 anatomy union/LV/RV、scar proposal、edema proposal T2-present、scar refiner ROI、edema refiner ROI、anchor preservation、branch arbitration consistency、bounded correction、component/remote-FP、no-T2 edema safety、dictionary entropy/coverage/load-balance、semantic family/interaction mass、prototype diversity/margin。必须输出 `loss_component_by_step.csv` 和 `loss_component_gradient_sanity.csv`。长期为 0 的 component 必须解释是合法不适用还是 bug；无解释的空 loss component 是 blocker。

如果 Cine 子线运行，必须把 CineMA 用作 anatomy/frame-quality/registration/temporal-dictionary evidence，而不是只写“尝试过”。必须记录 CineMA source path、version、weights/source status、input preprocessing、frame selection、class mapping、output label/probability shape、myocardium/anatomy Dice/HD95 against local reference 或 frame0 control，并明确 CineMA output 不能直接当 pathology prediction。若已有 CineMA output 可用却未使用，写 `M7_NEEDS_EVIDENCE`；若缺权重、缺输出或合规不明，写 `cinema_blocker_report.md` 并说明 exact blocker。

registration 必须是 same-safe-subset matrix，至少区分 frame0/ED identity control、CineMA frame-wise anatomy prior control、CineMA + ANTsPy SyN、CineMA + SimpleITK Demons/B-spline fallback、optical-flow/feature-warp proxy、VoxelMorph status。one-case SyN、frame0-only、untrained VoxelMorph、optical-flow descriptor 不得冒充 completed registration。若 registration matrix 没有至少一个合格 non-reference option，temporal dictionary 必须写 `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`，不得写 ready。

M7 result directory 必须是：

`results/20260705_srr_v3_m7_training_and_cine_utilization/`

必须写齐 shared M7 要求的所有文件：

- `result.md`
- `m7_execution_plan.md`
- `variant_matrix.csv`
- `training_adequacy_by_variant.csv`
- `one_batch_overfit_by_variant.csv`
- `training_curve_by_variant.csv`
- `validation_curve_by_variant.csv`
- `loss_component_by_step.csv`
- `loss_component_gradient_sanity.csv`
- `prediction_sanity_by_variant.csv`
- `same_split_help_harm.csv`
- `hard_subgroup_metrics.csv`
- `branch_arbitration_by_case.csv`
- `dictionary_prototype_usage_by_variant.csv`
- `proposal_refiner_by_case.csv`
- `no_t2_safety_by_variant.csv`
- `best_variant_decision.md`
- `failure_interpretation.md`
- `cinema_usage_report.md` if Cine subline runs, otherwise `cinema_blocker_report.md`
- `registration_same_subset_matrix.csv` if Cine subline runs
- `temporal_dictionary_evidence.csv` if temporal dictionary is attempted
- `cine_metrics_summary.csv` if Cine metrics are computed
- `label_export_qc.md`
- `commands_run.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

`completion_check.md` 只能写：

- `M7_READY_FOR_REVIEW`
- `M7_NEEDS_REVISION`
- `M7_NEEDS_EVIDENCE`
- `M7_NEEDS_MONITOR`
- `M7_BLOCKED_BY_M6`

不能写 `M7_READY_FOR_REVIEW` 的情况包括：任一必跑 MyoPS variant 没有训练且没有 blocker；required variant 被自行缩减；未跑 variant 被当作 skipped success；M7 退回旧 loss/model path；训练不足 1800 秒且没有 plateau；没有 same-split nnU-Net help/harm；没有 loss component 曲线；没有 hard subgroup metrics；no-T2 edema unsafe；best variant decision 不是由 metric table 决定；Cine 子线声称使用 CineMA 但没有 class mapping/output path/metric 或 blocker；registration 被 one-case SyN/untrained VoxelMorph/frame0-only 冒充完成；temporal dictionary 在 registration gap 下仍写成 ready；reviewer 所需轻量证据没有 git-tracked。

完成后 `git add -f` 并本地 commit M7 轻量证据和必要 first-party helper/source/config；不要提交 checkpoint、NIfTI、upload package、大日志、raw data、secrets、environment dump 或整棵 runtime tree；不要 push；不要写 `review.md`；不要启动后续 milestone。
```

## M7 executor follow-up 1: reviewer-blocker repair (continued)

```text
只执行 M7 follow-up 1 / continued：reviewer-blocker repair for `results/20260705_srr_v3_m7_training_and_cine_utilization/`。

开始前确认：

- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` 包含 `M7_AUDITED_NEEDS_REVISION`；否则写 `M7_CONTINUED_BLOCKED_BY_REVIEW_STATE` 并停止。
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 包含 `M6_AUDITED_GO`。
- 如果继续 Cine 子线，`results/20260705_srr_v3_m5_cine_secondary_contract/review.md` 包含 `M5_AUDITED_DIAGNOSTIC_GO`。

不要 validation packaging/upload，不要 hosted metric claim，不要 route promotion，不要 scientific stop，不要启动 M8，不要写 `review.md`。不得复制旧 M7 executor 段、旧 M5 evidence、旧 training curves、diagnostic-only rows 或自然语言解释来绕过本 follow-up 1 hard gates。本段是 M7 follow-up 1 的执行合同；原 M7 executor 段只保留为第一次 M7 run 的记录。后续 M7 follow-up 必须使用独立编号段落，不得复用一个笼统 `continued` 段。

### A. Training-loss validity gate

当前 75/75 `BACKWARD_FAILED` 是硬 blocker。不能通过重命名、修表格文字或 post-hoc logging fix 修复。Executor 必须先判断原 M7 training 是否真的使用 graph-connected expanded loss；如果原训练的 total loss 与 expanded loss components 脱节，或 gradient sanity 修复只证明 logging path 被修复，原 M7 training 结果不得继续作为有效 M7 evidence。

必须新增 `loss_graph_training_validity_report.md`，至少包含：

- 原 M7 training 使用的 total loss function 名称和代码路径；
- expanded loss components 是否进入 optimizer backward；
- `detach_metrics=True/False` 对 training loss 与 logging metrics 的影响；
- 是否需要 rerun training；
- 如果不 rerun，必须给出代码级证据说明原训练 already graph-connected；
- 如果 rerun，必须记录 rerun variant、steps、seconds、validation events、eval cases。

Rerun rule:

- 如果 gradient 修复后证明原训练不可信，不能写 `M7_CONTINUED_READY_FOR_REVIEW`，除非重新训练全部三个 required variants：`m7_full_srr_context_arbitration`、`m7_conservative_component_arbitration`、`m7_scar_precision_edema_safe`；
- 或至少重新训练一个预先指定的 primary variant，并把其他 variants 标为 `M7_NEEDS_EVIDENCE_NOT_COMPARABLE`，且 `best_variant_decision.md` 不得做 full variant ranking；
- 不得把旧 training curves 与新 gradient sanity 混合成同一个“有效训练证据”，除非 `loss_graph_training_validity_report.md` 证明二者同源、同代码路径、同 loss graph。

### B. 修复 loss gradient sanity

具体实现决定：

1. 修改 `src/care_myocardium/losses/srr_losses.py` 的 `srr_m6_expanded_total_loss`，增加或确认类似参数：`detach_metrics: bool = True`。
   - 默认 `True` 保持日志安全。
   - M7 gradient sanity 使用 `False`，返回 graph-connected component tensors。
   - 必须让以下 component 在 gradient sanity mode 下保持 graph：`loss_anatomy_union_lv_rv`、`loss_scar_proposal`、`loss_edema_proposal_t2_present_only`、`loss_scar_refiner_roi`、`loss_edema_refiner_t2_present_roi`、`loss_anchor_preservation_outside_roi`、`loss_branch_arbitration_consistency`、`loss_bounded_correction`、`loss_component_remote_fp`、`loss_no_t2_edema_safety`、`loss_dictionary_entropy_coverage_load_balance`、`loss_prototype_diversity_margin`、`m6_expanded_total_loss`。

2. 修改 `scripts/training/run_srr_propref_myops_fold0.py`：
   - step-1 gradient sanity 必须在 main training `loss.backward()` 之前执行；
   - 对每个 component 单独 `model.zero_grad(set_to_none=True)`，再 `component.backward(retain_graph=True)`；
   - 记录 `requires_grad`、`grad_l2_norm`、`param_with_grad_count`、`status`；
   - 只有真实 mask-gated 的 component 才允许 `LEGITIMATE_MASKED_NA`，并必须写 `zero_justification`、`batch_cases`、`t2_present_batch_fraction`、`target_voxel_count`。

3. 重新运行 M7 continued gradient sanity。可以使用已有 M7 checkpoint，也可以做一个短的 gradient-sanity-only run，但必须使用真实 M7 model、真实 patch、真实 label、真实 availability、真实 anchor/context，不得使用 M6 synthetic tensors。

4. 更新：
   - `loss_component_gradient_sanity.csv`
   - `loss_component_gradient_fix_report.md`
   - `loss_graph_training_validity_report.md`
   - relevant unit tests and `unit_test_report.md`

不得写 ready，如果任何 required component 仍是 `BACKWARD_FAILED`、`EVIDENCE_NOT_FOUND`、无解释 `ZERO_GRAD_OR_DETACHED`、或 `param_with_grad_count=0`。

### C. Formal-val insufficiency gate and hard subgroup coverage

实现确定性的 hard subgroup case selector，不允许临场挑 case。

新增或修改 first-party helper，例如 `select_m7_hard_subgroup_eval_cases`。它必须读取 fold split、case metadata、labels、nnU-Net anchor availability，并优先覆盖：

- `T2_present_complete`：C0+LGE+T2，优先 edema-labeled / GT-positive edema；
- `CenterB` / `CenterC`；
- `no_T2_empty_GT`；
- `remote_FP_positive`：nnU-Net anchor 或现有 M7 prediction remote FP count > 0；
- `small_lesion`：pathology GT voxel volume lower tertile；
- `large_lesion`：pathology GT voxel volume upper tertile；
- `GT_positive_scar` / `GT_positive_edema`。

如果数据中可用，M7 continued hard subgroup evidence 至少覆盖：

- at least 1 T2-present complete case；
- at least 1 GT-positive edema case；
- at least 1 GT-positive scar case；
- at least 1 CenterB or CenterC case；
- at least 1 remote-FP-positive case if anchor/prediction produces one；
- small-lesion and large-lesion strata if label volume permits。

如果任何组不可用，必须在 `hard_subgroup_coverage_report.md` 写 exact unavailable reason，并给出 case-pool audit，不能只写 “not found”。

新增或更新 `m7_case_pool_audit.csv`，字段至少包括：

`case_id, split_role, center, modality_group, t2_present, c0_present, scar_gt_voxels, edema_gt_voxels, scar_gt_positive, edema_gt_positive, anchor_remote_fp_scar, anchor_remote_fp_edema, small_lesion_flag, large_lesion_flag, selected_for_formal_val, selected_for_diagnostic_hardcase, eligible_for_best_variant_decision, exclusion_reason`

Formal best-variant metrics must prefer fold validation cases. If fold validation lacks a subgroup, create a separate `diagnostic_hardcase_eval` stratum from same-split train/hardcase cases, with explicit fields:

- `split_role=formal_val` or `diagnostic_train_hardcase`
- `eligible_for_best_variant_decision=true/false`
- `leakage_caveat`
- `reason_if_not_formal_val`

Diagnostic hardcase rows may support mechanism interpretation only. They must not be used for route promotion or formal best-variant selection. If formal validation rows still lack core subgroups such as T2-present, CenterB, CenterC, edema-positive, or remote-FP-positive, M7 continued cannot make a formal promotion-style best variant selection. It may write diagnostic mechanism interpretation only.

必须新增 `formal_val_coverage_limitations.md`，至少说明：

- formal_val 覆盖了哪些 center、modality pattern、T2-present、GT-positive scar/edema；
- 缺哪些 subgroup；
- diagnostic_train_hardcase 是否被使用；
- diagnostic rows 是否被排除在 formal best-variant decision 之外；
- 是否需要后续 stratified fold/eval expansion；
- 当前 conclusion 是否只能是 `NO_PROMOTION_SCIENTIFIC_UNRESOLVED` 或 `NEEDS_EVIDENCE`。

Required outputs:

- `m7_case_pool_audit.csv`
- `m7_hard_subgroup_case_manifest.csv` if retained as a selector manifest
- `formal_val_coverage_limitations.md`
- updated `same_split_help_harm.csv`
- updated `hard_subgroup_metrics.csv`
- `hard_subgroup_coverage_report.md`

Do not write ready if coverage remains all CenterA/LGE-only/no-T2, or if diagnostic hardcases are mixed into formal best-variant ranking. If required groups are genuinely unavailable, write `M7_NEEDS_EVIDENCE` or `M7_NEEDS_REVISION`, not ready.

### D. Cine decision separation

MyoPS blockers fixed does not imply Cine ready. Cine registration repair failure does not block MyoPS continued evidence, but it must block Cine readiness. `result.md`, `failure_interpretation.md`, and `completion_check.md` must separate:

- `myops_decision`
- `cine_decision`
- `combined_decision`

Rules:

- If Cine branch has no usable non-reference registration row, `cine_decision` must be `CINE_REGISTRATION_BLOCKED_AFTER_REPAIR_ATTEMPT` or `CINE_NEEDS_EVIDENCE`, not ready;
- If a usable non-reference registration row exists, executor must attempt temporal dictionary; not attempting it prevents ready;
- `combined_decision` cannot package MyoPS partial success plus Cine blocked as overall success.

### E. Cine registration minimum run gate

Do not only copy M5 evidence. Implement and run a M7 continued Cine registration repair helper, for example:

`scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py`

The helper must discover or generate CineMA/equivalent frame-wise anatomy outputs. If existing CineMA outputs are available, use them. If repo-local inference and local weights exist, run them. If not, record `CINEMA_OUTPUT_UNAVAILABLE` with exact missing paths.

Build a same-safe-subset with at least 3 cases and at least 2 non-reference frame pairs per case when data allow. Use ED/frame0 as reference and mid/ES or nearest available non-reference frames.

Run at least two non-reference registration families unless tools are unavailable:

- `SimpleITK_Demons` or `SimpleITK_BSpline` as the required fast classical path when SimpleITK is available;
- `ANTsPy_SyN` if installed, with import/availability check recorded if unavailable;
- optical-flow/feature-warp only as proxy, never as usable registration
- VoxelMorph only if trained/auditable weights exist; otherwise `UNTRAINED_NOT_USABLE`

If SimpleITK is available but neither Demons nor B-spline is run, M7 continued cannot be ready. Each usable candidate must have same-safe-subset rows; one-case smoke cannot represent the registration matrix. Frame0-only, one-case SyN, untrained VoxelMorph, and optical-flow proxy cannot be marked usable registration.

Each registration row must report myocardium Dice before/after, LV Dice before/after, HD95 before/after when computable, image NCC before/after, Jacobian/fold or displacement smoothness proxy, inverse/round-trip proxy where feasible, runtime seconds, and failure reason.

A row is usable only if it is non-reference and not one-case smoke, not frame0-only, not untrained VoxelMorph, and not optical-flow-only proxy, and it satisfies the helper's stated Dice/HD95/folding/round-trip thresholds. Use these default thresholds unless data force a documented revision:

- myocardium Dice improves by at least 0.02 on average, or is already >= 0.80 and HD95 does not worsen by more than 2 units;
- LV Dice does not worsen by more than 0.05;
- no severe folding/Jacobian warning;
- finite round-trip/inverse proxy within the helper threshold.

Required outputs:

- `cine_registration_repair_report.md`
- updated `registration_same_subset_matrix.csv`
- local runtime artifacts under a non-tracked runtime directory

### F. Temporal dictionary anti-cheat gate

If no usable non-reference registration row exists, `temporal_dictionary_evidence.csv` may only contain blocked rows and must not contain ready rows. If at least one usable non-reference registration option exists, attempt a minimal diagnostic temporal dictionary build. It must include:

- ED/reference anchor feature;
- selected non-reference frame feature;
- warped feature or warped probability;
- frame-quality score;
- motion-saliency score;
- registration-quality score;
- temporal representer slot usage;
- temporal aggregation output;
- local class_1 myocardium proxy;
- hosted metric caveat.

If no usable registration row exists after the repair attempt, write `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP_AFTER_REPAIR_ATTEMPT`. This is acceptable only if the registration helper actually ran and recorded failures.

Descriptor-only, no-warp, frame0-only, or one-case temporal rows cannot be marked ready.

### G. Strict validator known-bad cases

Update M7 continued strict validation so it fails closed, and output or update `strict_validator_report.md`. The report must record each known-bad packet's expected failure, actual exit code/status, and failure reason. Known-bad packets must include:

- all loss gradient rows `BACKWARD_FAILED`;
- gradient sanity fixed but training-loss validity missing;
- hard subgroup rows all CenterA/LGE-only/no-T2;
- diagnostic hardcase rows mixed into formal best-variant decision;
- Cine branch copies M5 evidence without new registration attempt;
- frame0-only or one-case SyN marked usable registration;
- untrained VoxelMorph marked usable;
- temporal dictionary marked ready despite no usable registration;
- completion_check says ready while any continued blocker remains.

### H. Aggregation and completion state

Update `scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py` so completion is fail-closed. It must explicitly check:

- no required loss component has failed/missing gradient evidence;
- `loss_graph_training_validity_report.md` exists and supports either original graph-connected training or required rerun evidence;
- hard subgroup coverage report exists and is not all missing;
- `m7_case_pool_audit.csv` exists with required fields;
- `formal_val_coverage_limitations.md` exists and prevents formal promotion-style selection when formal validation is insufficient;
- formal-val and diagnostic hardcase rows are separated;
- Cine registration repair was attempted if Cine subline is enabled;
- temporal dictionary is ready only if registration gate passes.
- strict validator known-bad cases fail closed.

Update these files in `results/20260705_srr_v3_m7_training_and_cine_utilization/`:

- `result.md`
- `m7_execution_plan.md`
- `loss_component_gradient_sanity.csv`
- `loss_component_gradient_fix_report.md`
- `loss_graph_training_validity_report.md`
- `m7_case_pool_audit.csv`
- `m7_hard_subgroup_case_manifest.csv`
- `formal_val_coverage_limitations.md`
- `hard_subgroup_coverage_report.md`
- `same_split_help_harm.csv`
- `hard_subgroup_metrics.csv`
- `best_variant_decision.md`
- `best_variant_decision_table.csv`
- `cine_registration_repair_report.md`
- `registration_same_subset_matrix.csv`
- `temporal_dictionary_evidence.csv`
- `cine_metrics_summary.csv` if Cine metrics are computed
- `failure_interpretation.md`
- `strict_validator_report.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`

`completion_check.md` may contain only:

- `M7_CONTINUED_READY_FOR_REVIEW`
- `M7_NEEDS_REVISION`
- `M7_NEEDS_EVIDENCE`
- `M7_NEEDS_MONITOR`
- `M7_BLOCKED_BY_M6`
- `M7_CONTINUED_BLOCKED_BY_REVIEW_STATE`

Do not write `M7_CONTINUED_READY_FOR_REVIEW` if any blocker above remains unresolved. `M7_CONTINUED_READY_FOR_REVIEW` only means continued blockers are ready for independent reviewer audit. It does not authorize route promotion, hosted metric claim, fold expansion, validation packaging/upload, challenge submission, M8, scientific stop, or leaderboard readiness.

Finish by force-adding and locally committing only the lightweight M7 continued packet plus necessary first-party helper/source/test files. Do not write `review.md` and do not start M8.
```

## M7 executor follow-up 2: leaderboard-oriented repair

```text
只执行 M7 follow-up 2：leaderboard-oriented repair after `M7_CONTINUED_AUDITED_NEEDS_REVISION`。

开始前必须确认：

- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` 存在且包含 `M7_CONTINUED_AUDITED_NEEDS_REVISION`；
- `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` 存在且包含 `M6_AUDITED_GO`；
- 当前任务仍是 M7 follow-up 2，不是 M8，不是 route promotion，不是 validation packaging/upload，不是 hosted metric claim，不是 challenge submission；
- 不要写 `review.md`，不要启动 M8。

本任务有两个层次。第一层是关闭最新 reviewer 指出的 strict-validator blocker。第二层是利用 M7/follow-up 1 的真实证据做 leaderboard-oriented method repair，不允许只修 validator 表格后停止。

Latest M7 continued review context that must be treated as evidence, not success:

- gradient sanity improved: `loss_component_gradient_sanity.csv` has no `BACKWARD_FAILED`, but strict validator proof is still insufficient;
- formal validation subgroup coverage improved, but best-variant decision remains non-promotional and scientifically unresolved;
- scar Dice deltas and edema Dice deltas remain tiny;
- Cine registration repair was attempted, but no non-reference row is usable for temporal dictionary;
- the next packet must convert useful M7 evidence into actual leaderboard-oriented repair instead of doing only validator bookkeeping.

Route objective remains strict. MyoPS SRR must become a baseline-preserving, error-targeted correction system over the nnU-Net anchor, with real dictionary/prototype/proposal/refiner/arbitration contributions on hard cases, especially T2-present edema, CenterB/CenterC, remote-FP-positive cases, and small/large lesion strata. Cine must not remain descriptor-only or frame0-only; registration-aware temporal retrieval is required, and if classical registration fails, executor must attempt stronger cropped/anatomy-guided registration escalation before preserving a gap.

### A. SRR-v3 image fidelity hard gate

M7 follow-up 2 must prove code/runtime fidelity to the SRR-v3 route diagram instead of relying on narrative claims. Create:

- `srr_v3_image_fidelity_checklist.csv`
- `architecture_gap_table.md`

The checklist must cover each row below with fields:

`route_component, expected_module, current_code_path, runtime_evidence_path, status, blocker_if_missing`

Required route components:

- availability-aware modality handling;
- modality-specific stems;
- strong encoder / nnU-Net context interface;
- semantic representation retrieval bank;
- shared/private/interaction dictionary slot usage;
- train/OOF prototype banks;
- scar proposal;
- edema proposal;
- anatomy union/LV/RV prior;
- distance/uncertainty/nnU-Net component evidence;
- scar soft-ROI refinement;
- edema soft-ROI refinement;
- baseline-preserving residual correction;
- scar/edema no-T2-safe output;
- expanded loss objectives;
- Cine registration-aware temporal retrieval.

`architecture_gap_table.md` must explain unresolved code gaps with exact code paths, evidence paths, and whether each gap blocks follow-up 2 readiness. Natural-language-only restatement is not enough. If a route component is only a stub, diagnostic export, or table column without runtime effect, mark `status=BLOCKER` or `status=PARTIAL_WITH_BLOCKER`.

### B. Branch arbitration no-op repair gate

Current code evidence shows `BranchArbitrationGate` exports `proposal_weight` and `refiner_weight`, but the audited formula path can still reduce final logits to `anchor_logits + srr_weight * bounded_delta`. M7 follow-up 2 must explicitly check and repair this no-op risk.

Create or update:

- `branch_arbitration_formula_report.md`
- `branch_arbitration_unit_tests.md`
- `arbitration_opening_diagnostics.csv`

Hard requirement:

- proposal/refiner/arbitration must directly affect final logits, or the executor must prove with code-level and runtime evidence that proposal/refiner contributions enter `srr_logits` and produce measurable nonzero final-logit changes inside ROI;
- `proposal_weight` and `refiner_weight` must not be only exported diagnostic columns;
- if the formula remains dead-weight, write `M7_FOLLOWUP2_NEEDS_REVISION` and list exact code blockers.

Unit tests must cover at least:

1. closed-gate / force segmentation fallback makes final labels exactly equal to the nnU-Net anchor;
2. high anchor uncertainty or injected anchor-error regions open the SRR correction gate;
3. changing proposal/refiner evidence causes nonzero final-logit changes inside ROI;
4. disabling proposal/refiner evidence removes their contribution and records it;
5. no-T2 cases keep edema final logits/decode/export safely blocked;
6. proposal/refiner weights cannot pass as mere diagnostic exports without prediction effect.

`arbitration_opening_diagnostics.csv` must include per-case/subgroup fields for anchor uncertainty, correction gate open rate, proposal/refiner weight summaries, final-logit delta magnitude in ROI, chosen source, no-T2 status, and blocker reason if no opening occurs.

### C. Modality order and no-zero-fill contract

Create:

- `modality_order_contract.md`
- `modality_order_unit_tests.md`

The contract must state the current implementation channel order and availability order, including the fact that current code uses `LGE,T2,C0` while the route diagram may describe semantic order as `LGE,C0,T2`. It must prove how the mapping is handled without semantic drift.

Required proof:

- `availability[:,1]` in current implementation is T2, not C0;
- no-T2 samples are not treated as edema-negative supervision or as real T2 evidence;
- no-T2 safety is enforced in edema loss, edema proposal, edema ROI/refiner, final logits, decode, and export;
- unavailable modalities are masked by availability and are not zero-filled as evidence.

Reviewer must be able to verify this from exact code paths and unit-test rows. A packet that omits modality order is not ready.

### D. 修复 strict validator：必须是真 known-bad fail-closed

当前 strict validator 是假的 fail-closed：它读取当前 good packet 的布尔状态，然后把 known-bad 名称标成 `PASS_FAIL_CLOSED`。这不满足 reviewer gate。

必须实现或新增一个可运行的 M7 continued/follow-up validator，例如：

`scripts/evaluation/validate_srr_v3_m7_continued_packet.py`

要求：

1. 接收 `--packet <result_dir>`。
2. 对真实 packet 成功时 exit code 为 0。
3. 对 bad packet 失败时 exit code 非 0。
4. 输出 JSON 或 Markdown summary。
5. 检查至少以下 gates：
   - loss gradient sanity rows 不得全 `BACKWARD_FAILED`；
   - `loss_graph_training_validity_report.md` 必须存在且说明 original training graph validity；
   - hard subgroup 不得全 CenterA/LGE-only/no-T2；
   - diagnostic hardcase rows 不得混入 formal best-variant decision；
   - Cine branch 必须有 M7 continued/follow-up registration repair attempt；
   - frame0-only / one-case SyN / untrained VoxelMorph 不得标为 usable registration；
   - temporal dictionary 不得在无 usable non-reference registration 时标 ready；
   - `completion_check.md` 不得在 blocker 未关闭时写 ready。

必须构造真实 known-bad fixtures。可以用临时目录复制当前 packet 后进行小范围 mutation。必须覆盖：

- `all_gradient_rows_backward_failed`;
- `missing_loss_graph_training_validity_report`;
- `hard_subgroup_all_centerA_lge_only_no_t2`;
- `diagnostic_rows_mixed_into_formal_best_variant`;
- `cine_copies_m5_no_new_registration_attempt`;
- `frame0_or_one_case_syn_marked_usable`;
- `untrained_voxelmorph_marked_usable`;
- `temporal_dictionary_ready_without_usable_registration`;
- `completion_ready_with_unresolved_blocker`.

Required output:

- `strict_validator_report.md`
- `strict_validator_report.csv`
- `validator_unit_test_report.md`
- `strict_validator_known_bad_cases/README.md` or equivalent fixture summary; do not commit large fixture directories.

Each row must include:

`known_bad_case, fixture_or_mutation, validator_command, expected_exit_code, actual_exit_code, expected_failure, actual_failure_reason, pass_fail_closed`

Do not mark M7 follow-up 2 ready unless every known-bad fixture fails with `actual_exit_code != 0`, or the validator CLI explicitly returns `ok=false` and the command is treated as a non-completion failure. Do not accept any exit-0 failure label for a known-bad fixture.

`validator_unit_test_report.md` must cover at least:

- good packet exits 0;
- every mutated bad packet exits nonzero;
- missing required files fail;
- completion ready with blocker fails;
- temporal dictionary ready without usable registration fails;
- diagnostic-hardcase rows mixed into formal decision fail.

### E. Training evidence validity and rerun decision

The latest M7 continued packet states that old training used graph-connected total loss and only logging metrics were detached. That may be true, but it is not enough for leaderboard-oriented repair because the metric deltas are negligible.

Update or create:

`loss_graph_training_validity_report.md`
`m7_followup2_training_rerun_decision.md`

The rerun decision must answer:

1. Did the original M7 training truly optimize the expanded loss graph?
2. Did each proposal/refiner/arbitration/dictionary component receive nonzero gradient on any real batch?
3. Did SRR actually open correction gates on hard cases, or did it remain near-anchor/no-op?
4. Did the trained variants materially change predictions in T2-present / CenterB / CenterC / remote-FP-positive rows?
5. If not, what architecture/training mechanism must be repaired before further training?

Hard rule:

If the original M7 training is graph-invalid, rerun at least the primary variant after fixing the loss. If graph-valid but scientifically no-op, do not pretend it succeeded. Instead run the mandatory MyoPS repairs in Section F, preserve the formal/diagnostic boundary in Section G, and run a short but real retraining/probe of the repaired primary variant.

Minimum retraining/probe requirement for follow-up 2:

- Train at least one pre-specified primary variant after mechanism repair.
- The default primary variant is `m7_full_srr_context_arbitration` unless the M7 evidence shows it is unsafe; if unsafe, choose `m7_scar_precision_edema_safe` and justify.
- Minimum: `optimizer_steps >= 1200` and `train_loop_seconds >= 900`, or explicit `M7_FOLLOWUP2_NEEDS_MONITOR` if the job is still running.
- Preferred: `optimizer_steps >= 3000` and `train_loop_seconds >= 1800`.
- Use hardcase-aware sampling or batch construction so that T2-present and GT-positive edema appear in gradient sanity and validation events when available.
- Do not rank all variants if only one is retrained. Mark non-rerun variants `NOT_COMPARABLE_AFTER_FOLLOWUP2_REPAIR`.

Required files:

- `m7_followup2_training_rerun_decision.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`

### F. MyoPS mechanism no-op diagnosis and mandatory repair

The current M7/continued evidence is not enough because best-variant deltas are tiny and every row remains `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`. The next executor must diagnose why SRR is not materially helping.

Create:

`m7_followup2_mechanism_noop_diagnosis.md`
`srr_contribution_by_case.csv`
`arbitration_opening_diagnostics.csv`
`proposal_refiner_effectiveness.csv`

Required diagnostics:

1. `anchor_delta_rate`: fraction of voxels changed vs nnU-Net anchor by class and case.
2. `correction_gate_open_rate`: scar/edema gate opening by case, subgroup, and variant.
3. `proposal_recall_proxy`: whether GT-positive scar/edema regions are inside proposal/ROI.
4. `remote_fp_suppression_proxy`: whether SRR reduces or increases remote false positives.
5. `refiner_delta_magnitude`: whether bounded delta is nonzero inside ROI.
6. `arbitration_chosen_source`: distribution over anchor/SRR/proposal/refiner per class and subgroup.
7. `prototype_margin`: positive-vs-safe-negative similarity margins on GT-positive and hard-negative regions.
8. `dictionary_family_mass`: shared/private/interaction mass by class and subgroup.
9. `T2_signal_use`: whether T2-private / T2 interaction evidence is active on T2-present edema rows and masked on no-T2 rows.
10. `hardcase_effect`: deltas on T2-present, CenterB/CenterC, remote-FP-positive, GT-positive edema, small lesion and large lesion strata.

Because M7 continued already shows near-zero best-variant deltas, follow-up 2 has a minimum mandatory repair floor. The executor must execute both C1 and C2 below. C3 and C4 become mandatory when their diagnostic triggers are present. The executor may not write "diagnosis shows no repair needed" as an escape hatch.

#### F1. Mandatory gate opening calibration / correction-opportunity objective

Add a controlled gate-opening calibration and correction-opportunity objective:

- initialize arbitration bias to open SRR only in high anchor-uncertainty or remote-FP-positive regions;
- add `loss_correction_opportunity` on train/OOF anchor-error masks;
- keep exact anchor fallback outside correction mask;
- prove no-T2 edema safety remains.

Required evidence must appear in `followup2_repair_summary.md`, `followup2_loss_component_by_step.csv`, `arbitration_opening_diagnostics.csv`, and `followup2_same_split_help_harm.csv`.

#### F2. Mandatory hardcase-aware sampler

Add deterministic hardcase-aware sampling so T2-present, GT-positive edema, CenterB/CenterC, remote-FP-positive, scar-positive, and no-T2 safety cases enter training/gradient sanity/validation events when available.

`followup2_batch_composition.csv` is required for every retraining/probe. It must record case IDs, split role, center, modality group, T2 availability, scar/edema GT positivity, remote-FP flags, no-T2 safety role, and whether each row was used in training, gradient sanity, or validation.

#### F3. Conditional prototype / hard-negative memory repair

If prototype margins are weak or remote FP persists:

- refresh scar-safe-negative and edema-safe-negative banks from hard FP components;
- for edema, only use T2-present safe negatives;
- add margin loss on hard negatives;
- report prototype source and leakage checks.

#### F4. Conditional proposal/refiner ROI repair

If proposals miss GT-positive pathology or ROI is too small/too large:

- scar: smaller but recall-safe ROI with remote-FP penalty;
- edema: larger T2-conditioned context ROI, lower threshold, boundary uncertainty;
- report ROI volume ratio, recall proxy, precision proxy, and component burden.

If C1 or C2 cannot be implemented, or if C3/C4 triggers are present but the repair cannot be implemented, write `M7_FOLLOWUP2_NEEDS_REVISION` and explain exact code blocker. Do not use extra tables as a substitute for repair.

### G. Formal validation and diagnostic hardcase decision boundary

Update:

`m7_case_pool_audit.csv`
`formal_val_coverage_limitations.md`
`hard_subgroup_coverage_report.md`

Formal-val rows may be used for metric decision. Diagnostic train/hardcase rows may only support mechanism diagnosis.

Required fields remain:

`case_id, split_role, center, modality_group, t2_present, c0_present, scar_gt_voxels, edema_gt_voxels, scar_gt_positive, edema_gt_positive, anchor_remote_fp_scar, anchor_remote_fp_edema, small_lesion_flag, large_lesion_flag, selected_for_formal_val, selected_for_diagnostic_hardcase, eligible_for_best_variant_decision, exclusion_reason`

Additional required fields:

`used_in_gradient_sanity, used_in_retraining, used_in_mechanism_diagnosis, eligible_for_promotion_decision`

Hard rule:

If formal-val coverage is still too small for T2-present/CenterB/CenterC conclusions, `best_variant_decision.md` must remain `NO_PROMOTION_SCIENTIFIC_UNRESOLVED` or `NEEDS_EVIDENCE`. Diagnostic hardcases cannot be used to select a challenge candidate.

### H. Cine registration follow-up 2 escalation

The current continued packet attempted SimpleITK/ANTsPy/VoxelMorph availability, but no non-reference registration row is usable. That is honest but not enough for a leaderboard-oriented Cine route.

The follow-up 2 executor must attempt a stronger cropped/anatomy-guided registration escalation before preserving the gap again.

Create or update:

`scripts/evaluation/run_srr_v3_m7_cine_registration_followup2.py`
`cine_registration_followup2_report.md`
`registration_same_subset_matrix.csv`
`temporal_dictionary_evidence.csv`

Required new registration candidates:

1. `heart_crop_center_of_mass_affine`
   - Crop to a heart/anatomy bounding box.
   - Align reference and moving anatomy by center of mass / translation / scale if possible.
   - This is a simple but robust baseline and must be attempted if masks/probabilities exist.
2. `heart_crop_SimpleITK_BSpline_or_Demons_tuned`
   - Run multi-resolution registration inside cropped ROI.
   - Use anatomy/probability distance maps if available.
   - Report before/after anatomy Dice/HD95 and image NCC.
3. `ANTsPy_SyN_cropped_subset`
   - If ANTsPy is installed, rerun on cropped ROI for at least 3 cases x 2 non-reference pairs when feasible.
   - If not installed, record import failure and environment.
4. `optical_flow_proxy_warp`
   - Still only proxy, but report whether it improves anatomy metrics.
   - It cannot be the only usable registration unless explicitly reclassified by reviewer in a later task.
5. `trained_or_trainable_voxelmorph_probe`
   - Only if trained weights exist or a short self-supervised training run is feasible.
   - Untrained VoxelMorph remains negative control.

A usable row must include:

`method, case_id, reference_frame_id, moving_frame_id, before_myo_dice, after_myo_dice, before_lv_dice, after_lv_dice, before_hd95, after_hd95, before_ncc, after_ncc, displacement_smoothness, jacobian_or_fold_proxy, roundtrip_proxy, runtime_seconds, usable_for_temporal_dictionary, failure_reason`

If at least one usable row exists, temporal dictionary follow-up 2 is mandatory and must include warped non-reference evidence. If none exists, write `CINE_REGISTRATION_BLOCKED_AFTER_FOLLOWUP2_ESCALATION`, not ready.

### I. Temporal dictionary anti-cheat

If no usable non-reference registration row exists, `temporal_dictionary_evidence.csv` must contain only blocked rows.

If usable registration exists, temporal dictionary must contain:

- ED/reference anchor feature;
- selected non-reference frame id;
- warped image/probability/feature source;
- registration quality;
- frame quality;
- motion saliency;
- temporal representer slot usage;
- aggregation output summary;
- local class_1 myocardium proxy;
- hosted metric caveat.

Descriptor-only, no-warp, frame0-only dictionary cannot be marked ready.

### J. Required follow-up 2 outputs

Write all outputs under:

`results/20260705_srr_v3_m7_training_and_cine_utilization/`

Required new or updated files:

- `result.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md` or equivalent fixture summary
- `validator_unit_test_report.md`
- `srr_v3_image_fidelity_checklist.csv`
- `architecture_gap_table.md`
- `branch_arbitration_formula_report.md`
- `branch_arbitration_unit_tests.md`
- `modality_order_contract.md`
- `modality_order_unit_tests.md`
- `loss_graph_training_validity_report.md`
- `m7_followup2_training_rerun_decision.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv` for every retraining/probe
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_mechanism_noop_diagnosis.md`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `followup2_repair_summary.md`
- `route_to_leaderboard_gap_report.md`
- `m7_case_pool_audit.csv`
- `formal_val_coverage_limitations.md`
- `hard_subgroup_coverage_report.md`
- `cine_registration_followup2_report.md`
- `registration_same_subset_matrix.csv`
- `temporal_dictionary_evidence.csv`
- `cine_metrics_summary.csv` if computed
- `failure_interpretation.md`

If a file is not applicable, it must exist with an explicit `NOT_APPLICABLE_WITH_REASON` section. Missing required files are not allowed.

`followup2_repair_summary.md` must state which repairs were executed, which were not, why, and whether SRR still appears no-op. `route_to_leaderboard_gap_report.md` must state what remains before leaderboard-ready/challenge-ready status; it must not present follow-up 2 as challenge-ready.

### K. Completion states

`completion_check.md` may contain only:

- `M7_FOLLOWUP2_READY_FOR_REVIEW`
- `M7_FOLLOWUP2_NEEDS_REVISION`
- `M7_FOLLOWUP2_NEEDS_EVIDENCE`
- `M7_FOLLOWUP2_NEEDS_MONITOR`
- `M7_FOLLOWUP2_BLOCKED_BY_REVIEW_STATE`
- `M7_BLOCKED_BY_M6`

Do not write `M7_FOLLOWUP2_READY_FOR_REVIEW` if:

- strict validator does not run real known-bad fixtures;
- strict validator uses exit-0 "controlled fail" wording instead of nonzero bad-fixture failures;
- `validator_unit_test_report.md` is missing or does not cover required bad cases;
- SRR-v3 image fidelity checklist or architecture gap table is missing, incomplete, or natural-language-only;
- branch arbitration still leaves proposal/refiner as dead-weight diagnostic exports;
- modality order/no-zero-fill contract or unit tests are missing;
- current training evidence is graph-invalid and no rerun/probe was done;
- mechanism no-op diagnosis is missing;
- C1 gate-opening calibration and C2 hardcase-aware sampler were not both implemented when retraining/probe occurs;
- SRR contribution remains near-zero and no concrete repair was attempted;
- formal/diagnostic rows are mixed in formal decision;
- Cine registration follow-up 2 escalation was not attempted;
- temporal dictionary is marked ready without usable registration;
- no-promotion/scientific unresolved boundary is missing;
- `route_to_leaderboard_gap_report.md` is missing or claims leaderboard/challenge readiness;
- route promotion, hosted metric claim, validation packaging/upload, M8, fold expansion, challenge submission, scientific stop, or leaderboard readiness is claimed.

Finish by force-adding and locally committing only lightweight evidence plus necessary first-party helper/source/test files. Do not commit checkpoints, NIfTI predictions, upload packages, large logs, raw data, secrets, environment dumps, or runtime trees. Do not write `review.md`. Do not push.
```

## M7 executor follow-up 3: completion-safe re-aggregation and temporal dictionary repair

M7 follow-up3 remains M7. It is not M8, not route promotion, not validation packaging/upload, not a hosted metric claim, not challenge submission, not fold expansion, not scientific stop, and not leaderboard readiness.

Follow-up3 only repairs two hard follow-up2 problems:

- the follow-up2 executor submitted a `M7_FOLLOWUP2_NEEDS_MONITOR` / `PENDING_MONITOR` monitor packet, including Slurm job `58021931`, as if it were reviewable completion evidence;
- Cine follow-up2 produced at least one usable registration row for temporal dictionary construction, but temporal dictionary execution was left as `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED`.

```text
只执行 M7 follow-up3：completion-safe re-aggregation and temporal dictionary repair after `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`.

Scope:

- This is still M7.
- This is not M8.
- This is not route promotion.
- This is not validation packaging/upload.
- This is not a hosted metric claim.
- This is not challenge submission.
- This is not fold expansion.
- This is not scientific stop.
- This is not leaderboard readiness.
- Do not train a new route unless an already-submitted follow-up2 probe must be re-aggregated from completed runtime outputs.
- Do not write `review.md`.
- Do not push.

Start gates:

- Read `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`; continue only if the latest review decision is `M7_FOLLOWUP2_AUDITED_NEEDS_EVIDENCE`.
- Read the M6 review state required by M7; if M6 is not `M6_AUDITED_GO`, write `M7_BLOCKED_BY_M6`.
- If the review state does not authorize this follow-up3 repair, write `M7_FOLLOWUP3_BLOCKED_BY_REVIEW_STATE`.

Must read before edits:

- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/result.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/completion_check.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/followup2_training_adequacy.csv`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/commands_run.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/registration_same_subset_matrix.csv`
- existing `temporal_dictionary_*` files, if present
- runtime output path/logs for Slurm job `58021931` or any superseding follow-up2 job recorded in `commands_run.md`
- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`

### A. MONITOR_PACKET_IS_NOT_COMPLETION hard gate

Executor must explicitly read and report:

- `completion_check.md`;
- `followup2_training_adequacy.csv`;
- `commands_run.md`;
- Slurm job id, normally `58021931` unless a superseding job is recorded;
- `sacct` or equivalent Slurm completion record;
- current `squeue` state if the job may still exist;
- runtime output path and log path;
- whether the tracked follow-up2 packet already contains aggregation outputs written after job completion.

Use commands equivalent to:

```bash
squeue -j 58021931 -o '%i|%P|%j|%T|%M|%l|%R'
sacct -j 58021931 --format=JobID,JobName,Partition,State,Elapsed,ExitCode,Start,End -P
```

If `completion_check.md` is `M7_FOLLOWUP2_NEEDS_MONITOR`, if `followup2_training_adequacy.csv` still contains `PENDING_MONITOR`, or if `commands_run.md` only shows job submitted/pending without completed post-job aggregation outputs, do not write ready. First re-aggregate completed job outputs, or write a non-ready state.

If the job is still pending, running, suspended, unresolvable by `sacct`, or waiting for scheduler evidence, write `M7_FOLLOWUP3_NEEDS_MONITOR`. A monitor packet is not a normal review packet; if a monitor packet must be committed, `review_request.md` must say `DO_NOT_REVIEW_MONITOR_PACKET`.

### B. Completed Slurm job re-aggregation

If Slurm job `58021931` or a superseding follow-up2 job completed with exit code `0:0`, executor must:

- find the runtime outputs and logs;
- rerun or invoke the M7 follow-up2 aggregator/evidence collector;
- merge runtime outputs into tracked lightweight files;
- remove stale monitor placeholders from tracked decision files;
- record job id, state, exit code, runtime seconds, output/log paths, aggregation command, and aggregation exit code.

Required updated tracked files:

- `result.md`
- `completion_check.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_training_rerun_decision.md`
- `failure_interpretation.md`
- `commands_run.md`
- `MANIFEST.md`

Also update when evidence exists:

- `followup2_loss_component_gradient_sanity.csv`
- `followup2_batch_composition.csv`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `followup2_repair_summary.md`
- `route_to_leaderboard_gap_report.md`

Create or update:

- `m7_followup3_runtime_reaggregation_report.md`
- `m7_followup3_slurm_completion_record.md`

Those reports must include: `job_id`, `job_state`, `exit_code`, `runtime_seconds`, `start_time`, `end_time`, `runtime_output_path`, `log_path`, `aggregation_command`, `aggregation_exit_code`, `regenerated_files`, `files_still_missing`, and `tracked_packet_monitor_placeholders_remaining`.

If the job completed but runtime outputs are missing, corrupt, unwritten, or cannot be recovered by the aggregator, write `M7_FOLLOWUP3_NEEDS_EVIDENCE`, not ready.

### C. MyoPS follow-up2 result aggregation gate

If the primary MyoPS probe is incomplete, monitor-only, or still lacks job-completion aggregation, follow-up3 cannot claim M7 follow-up2 completion. Write separate decisions:

- `myops_decision: M7_FOLLOWUP3_NEEDS_MONITOR` or `M7_FOLLOWUP3_NEEDS_EVIDENCE`
- `cine_decision: ...`
- `combined_decision: ...`

Do not package a mixed MyoPS/Cine state as overall success.

If MyoPS completed but metrics remain no-op, update:

- `m7_followup2_mechanism_noop_diagnosis.md`
- `srr_contribution_by_case.csv`
- `arbitration_opening_diagnostics.csv`
- `proposal_refiner_effectiveness.csv`
- `failure_interpretation.md`
- `route_to_leaderboard_gap_report.md`

State whether another mechanism repair is required. No-op or undertrained evidence may support `NEEDS_EVIDENCE` / `NEEDS_REVISION` / `SCIENTIFIC_UNRESOLVED`; it never authorizes route promotion or scientific stop by itself.

### D. Temporal dictionary forced closure

Executor must inspect `registration_same_subset_matrix.csv`. If any row has:

- `usable_for_temporal_dictionary=True`, or
- equivalent status such as `m7_continued_decision=USABLE_NONREFERENCE_REGISTRATION_ROW`,

then temporal dictionary follow-up3 is mandatory. Executor may not write `TEMPORAL_DICTIONARY_FOLLOWUP2_REQUIRED_NOT_EXECUTED` and still mark the packet ready.

Temporal dictionary follow-up3 must output or update:

- `temporal_dictionary_evidence.csv`
- `temporal_dictionary_index.json`
- `temporal_dictionary_case_summary.csv`
- `temporal_aggregation_metrics.csv`
- `frame0_vs_temporal_help_harm.csv`
- `cine_metrics_summary.csv`
- `cine_temporal_dictionary_followup3_report.md`

Every usable registration row must have a temporal dictionary attempt. If only a subset is attempted, write the deterministic selection rule and the reason each usable-but-unattempted row was not executed.

### E. Temporal dictionary minimum content

If any usable non-reference registration row exists, temporal dictionary evidence must not be descriptor-only, no-warp-only, or frame0-only. It must include:

- ED/reference anchor feature;
- selected non-reference frame id;
- warped image/probability/feature source;
- registration method and registration quality;
- frame-quality score;
- motion-saliency score;
- temporal representer slot usage;
- temporal aggregation output summary;
- local class_1 myocardium proxy;
- class_3 sanity if available;
- hosted metric caveat;
- frame0/control comparison.

If warped evidence cannot be generated, executor must either revoke the usable registration judgment in `registration_same_subset_matrix.csv` with a concrete failure reason, or write `TEMPORAL_DICTIONARY_BLOCKED_BY_USABLE_ROW_INVALIDATED` with evidence. Executor cannot keep a usable registration row and skip temporal dictionary execution.

### F. Strict validator

Add or update `scripts/evaluation/validate_srr_v3_m7_followup3_packet.py`, or the existing M7 validator if that is the governed entrypoint. The validator must accept a packet path and exit 0 only for a reviewable packet. It must exit nonzero for bad packets.

Known-bad fixtures must include:

- `completion_check.md` says `M7_FOLLOWUP2_NEEDS_MONITOR` but packet is marked ready;
- `followup2_training_adequacy.csv` contains `PENDING_MONITOR` but packet is marked ready;
- Slurm job submitted/pending only, without completed aggregation;
- Slurm job completed but runtime output not aggregated into tracked evidence;
- `usable_for_temporal_dictionary=True` but `temporal_dictionary_evidence.csv` is missing or not executed;
- temporal dictionary marked ready but evidence is only frame0/no-warp/descriptor;
- diagnostic hardcase rows used for formal best-variant decision;
- completion ready while any MyoPS or Cine blocker remains.

Validator evidence must include:

- `strict_validator_report.md`
- `strict_validator_report.csv`
- `strict_validator_known_bad_cases/README.md`
- `validator_unit_test_report.md`

Each known-bad row must record `fixture_name`, `expected_failure`, `actual_exit_code`, `actual_status`, `failure_reason`, and `passed_fail_closed`.

### G. Required output set

The follow-up3 tracked packet must include or update:

- `result.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`
- `commands_run.md`
- `m7_followup3_runtime_reaggregation_report.md`
- `m7_followup3_slurm_completion_record.md`
- `followup2_training_adequacy.csv`
- `followup2_loss_component_by_step.csv`
- `followup2_same_split_help_harm.csv`
- `followup2_hard_subgroup_metrics.csv`
- `m7_followup2_training_rerun_decision.md`
- `failure_interpretation.md`
- `temporal_dictionary_evidence.csv`, when usable registration exists
- `temporal_dictionary_index.json`, when usable registration exists
- `temporal_dictionary_case_summary.csv`, when usable registration exists
- `temporal_aggregation_metrics.csv`, when usable registration exists
- `frame0_vs_temporal_help_harm.csv`, when usable registration exists
- `cine_metrics_summary.csv`, when usable registration exists
- `cine_temporal_dictionary_followup3_report.md`, when usable registration exists
- `strict_validator_report.md`
- `strict_validator_report.csv`
- `validator_unit_test_report.md`
- `route_to_leaderboard_gap_report.md`

`route_to_leaderboard_gap_report.md` must explicitly say what still blocks leaderboard readiness and must not claim challenge-ready status.

### H. Completion states

`completion_check.md` may only use:

- `M7_FOLLOWUP3_READY_FOR_REVIEW`
- `M7_FOLLOWUP3_NEEDS_MONITOR`
- `M7_FOLLOWUP3_NEEDS_EVIDENCE`
- `M7_FOLLOWUP3_NEEDS_REVISION`
- `M7_FOLLOWUP3_BLOCKED_BY_REVIEW_STATE`
- `M7_BLOCKED_BY_M6`

Do not write ready if:

- follow-up2 training adequacy still contains `PENDING_MONITOR`;
- Slurm job completion outputs were not aggregated;
- usable registration exists but temporal dictionary was not executed;
- temporal dictionary evidence is descriptor-only, frame0-only, or no-warp-only;
- strict validator is not true known-bad fail-closed;
- MyoPS and Cine decisions are merged into an overall success despite blockers;
- route promotion, hosted metric claim, validation packaging/upload, M8, fold expansion, challenge submission, scientific stop, or leaderboard readiness is declared.

Finish by force-adding and locally committing only lightweight prompt/code/evidence files required by the governed packet. Do not commit checkpoints, NIfTI predictions, upload packages, large logs, raw data, secrets, environment dumps, or runtime trees. Do not write `review.md`. Do not push.
```

## M8 executor: editor-grade leaderboard sprint

```text
只执行 M8：editor-grade SRR-v3 leaderboard sprint after `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`.

M8 scope:

- MyoPS is the primary line.
- Cine is secondary but mandatory.
- M8 is not validation packaging/upload.
- M8 is not hosted metric claim.
- M8 is not challenge submission.
- M8 is not scientific stop.
- M8 is not M9.
- Do not write `review.md`.
- Do not approve yourself.
- Do not push.

Start gates:

- Confirm `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md` exists and contains `M7_FOLLOWUP3_AUDITED_GO_FOR_NEXT_PLANNING`; otherwise write `M8_BLOCKED_BY_M7`.
- Confirm `results/20260705_srr_v3_m6_myops_concrete_architecture_repair/review.md` exists and contains `M6_AUDITED_GO`; otherwise write `M8_BLOCKED_BY_M7`.
- Confirm this M8 executor section is active in `prompts/shared/EXECUTOR_PROMPTS.md` and the M8 reviewer section is active in `prompts/shared/REVIEWER_PROMPTS.md`; otherwise write `M8_NEEDS_REVISION` and do not execute the milestone.
- Execute `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md` before route planning. The visual route diagrams must be read from ChatGPT Project background materials / current thread visual materials using canonical version references `images/SRR-v2.png`, `images/SRR-v2.5.png`, `images/SRR-v3.png`, and any later SRR/MyoPS diagrams.

Must read:

- `prompts/shared/EXECUTOR_PROMPTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`
- `prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/architecture_contract.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/interface_contract.md`
- `results/20260705_srr_v3_m0_architecture_master_contract/metric_contract.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/review.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/route_to_leaderboard_gap_report.md`
- `results/20260705_srr_v3_m7_training_and_cine_utilization/failure_interpretation.md`

Write `m8_route_objective.md` before scientific work. It must state that SRR-MyoPS is availability-aware selective retrieval plus semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, explicit losses/objectives, and nnU-Net anchor/context/evidence/safety. nnU-Net or another strong segmenter can be anchor/context/evidence/safety, but SRR cannot be reduced to optional post-processing or generic fallback. Cine is registration-aware temporal retrieval with warped non-reference evidence.

### A. M8 training budget semantics

M8 is a leaderboard sprint. It must not complete with a smoke, placeholder, monitor packet, submitted-only Slurm job, or a few-minute probe.

Training budget rule:

- Cumulative MyoPS `train_loop_seconds` across real M8 MyoPS training, continued training, targeted repair, and targeted probe runs must be at least `28800` seconds unless the packet is explicitly `M8_RESOURCE_BLOCKED` or the user has approved a written exception.
- A single job, candidate, or variant does not need to run 8 hours by itself.
- The 8-hour aggregate must come from real training loops only. Do not count queue time, monitor time, aggregation, evaluation-only, data preprocessing, export, registration-only Cine work, or validation packaging.
- Any actual training/probe used for a formal decision must not be a minutes-long smoke. Each such run must have `train_loop_seconds >= 900` and at least 3 validation events, or must provide explicit plateau/early-stop evidence.
- At least one primary candidate must be a serious long candidate, recommended `train_loop_seconds >= 7200` or `optimizer_steps >= 6000`, unless resources block it.
- If a job is pending/running or waiting on scheduler accounting, write `M8_NEEDS_MONITOR_NO_REVIEW`; do not create a normal ready review packet.
- After a job completes, rerun the aggregator/evidence collector and merge runtime outputs into tracked lightweight files before requesting review.

Write `m8_training_budget_ledger.csv` with fields:

`run_id, variant, job_id, is_training_run, is_eval_only, start_time, end_time, train_loop_seconds, optimizer_steps, validation_event_count, checkpoint_in, checkpoint_out, included_in_8h_budget, exclusion_reason`

`m8_training_budget_ledger.csv` must prove the total included real training loop seconds. If it is missing or the included sum is below `28800` without resource/user exception, do not write `M8_READY_FOR_REVIEW`.

### B. M8 variant config contract

Create `m8_variant_config_contract.yaml` or `m8_variant_config_contract.json`. The training code must read this config, or an equivalent code path must prove the same fields are used. Natural-language variant descriptions are not enough.

Each variant must specify encoder profile, dictionary slot counts, router bias / gate-opening strategy, prototype bank source, hard-negative mining source, proposal thresholds, ROI dilation / crop policy, loss weights, sampler quotas, training stages, optimizer / LR / scheduler, checkpoint selection rule, inference arbitration rule, and no-T2 edema safety rule.

Required variants:

- `m8_full_srr_context_arbitration_longrun`: full dictionary, correction opportunity, gate-opening curriculum, hard-negative memory, full proposal/refiner/arbitration final-logit effect.
- `m8_scar_precision_edema_safe_longrun`: scar precision, no-T2 safety, conservative arbitration, remote-FP suppression, scar HD95 guard.
- `m8_t2_centerC_edema_repair_longrun`: T2-present edema, CenterB/CenterC oversampling, larger edema ROI, T2-private plus LGE-T2 interaction mass floor, edema recall and HD95 guard.

Write `m8_variant_matrix.csv` and include the config path and code path that reads or enforces each variant. If variants only differ by name, write `M8_NEEDS_REVISION`.

### C. Architecture gap closure

Write `m8_architecture_gap_closure_table.csv` with fields:

`route_component, m7_status, required_m8_closure, closure_status, code_path, config_path, runtime_evidence_path, unit_test_or_validator_path, reviewer_repro_command, blocker_if_not_closed`

Allowed `closure_status` values are `CLOSED_WITH_RUNTIME_EVIDENCE`, `CLOSED_BY_PREVIOUS_AUDITED_EVIDENCE`, `RESOURCE_BLOCKED_WITH_COMMANDS`, `NEEDS_REVISION`, and `NEEDS_EVIDENCE`. Do not write a bare `CLOSED`.

If closure reuses M7 evidence, state why that audited evidence still applies to M8. If M8 changes the code path, config, training schedule, decoder, or inference arbitration, old M7 evidence cannot be directly reused.

Rows must cover availability-aware modality handling; modality-specific stems and modality-order contract; strong encoder/context; nnU-Net anchor probability/logit/component/uncertainty interface; shared/private/interaction dictionary slot usage; train/OOF prototype banks; hard-negative memory; scar proposal; edema proposal; anatomy union/LV/RV distance/uncertainty support; scar soft-ROI refinement; edema soft-ROI refinement; branch arbitration final-logit effect; baseline-preserving fallback; expanded loss objectives; per-case tensor export; no-T2 edema safety; same-split help/harm evaluator; Cine registration-aware temporal dictionary.

### D. Hardcase-aware training and batch evidence

Implement or harden a hardcase-aware sampler. Write `m8_batch_composition.csv` and `m8_hardcase_sampling_report.md`.

`m8_batch_composition.csv` must report per step/epoch:

`step, variant, case_id, center, modality_group, t2_present, c0_present, scar_gt_positive, edema_gt_positive, no_t2_safety_case, remote_fp_positive, small_lesion, large_lesion, selected_reason, loss_terms_active`

Rejectable executor states include batches dominated over the run by LGE-only/no-T2/easy cases; T2-present or edema-positive cases absent or far below their available-data proportion; no-T2 cases used as edema negative supervision; sampler explained only in prose without per-step evidence.

### E. Prototype, hard-negative, proposal, refiner, and contribution evidence

Write `m8_prototype_bank_summary.json`, `m8_hard_negative_memory_summary.csv`, `m8_prototype_margin_by_case.csv`, `m8_proposal_refiner_recall_precision.csv`, `m8_srr_contribution_by_case.csv`, and `m8_arbitration_opening_diagnostics.csv`.

`m8_srr_contribution_by_case.csv` must export real per-case `anchor_delta_rate`; `EVIDENCE_NOT_EXPORTED_PER_CASE` is not allowed. Required fields:

`variant, checkpoint, decode_mode, case_id, center, modality_group, t2_present, class_name, anchor_delta_rate, final_delta_rate, correction_gate_open_rate, srr_weight_mean, proposal_weight_mean, refiner_weight_mean, fallback_weight_mean, final_logit_delta_abs_mean, roi_delta_abs_mean, proposal_recall_proxy, proposal_precision_proxy, refiner_delta_magnitude, no_t2_edema_voxels, dice_delta, hd95_delta, remote_fp_delta, component_count_delta, source_prediction_path`

If per-case delta/contribution export is missing, M8 cannot be ready.

### F. Loss, validation, and broad same-split formal evidence

Write `m8_loss_schedule.md`, `m8_training_curves.csv`, `m8_validation_events.csv`, `m8_loss_component_by_step.csv`, `m8_loss_component_gradient_sanity.csv`, `m8_formal_case_manifest.csv`, `m8_same_split_help_harm.csv`, `m8_hard_subgroup_metrics.csv`, and `m8_component_remote_fp_hd95_report.csv`.

Formal evidence must be broad, not narrow/easy-only. It must include T2-present complete cases, CenterB/CenterC when available, scar-positive cases, GT-positive edema cases, no-T2 safety cases, and remote-FP-positive cases when those cases exist in the same-split pool.

Primary MyoPS metrics are `myops_scar` and `myops_edema`. Do not use foreground mean or empty-GT edema to hide failure.

### G. MyoPS local candidate assembly

M8 must assemble local candidates, not only train raw variants. Write `m8_local_inference_recipe.md`, `m8_candidate_assembly_matrix.csv`, `m8_export_dry_run_qc.md`, `m8_best_variant_decision_table.csv`, and `m8_route_promotion_decision.md`.

Compare at least:

- A. nnU-Net anchor control;
- B. best single SRR variant;
- C. anchor-preserving SRR correction with conservative fallback;
- D. SRR plus component/remote-FP postprocessing;
- E. SRR plus TTA/flip ensemble if feasible;
- F. SRR variant ensemble or checkpoint ensemble if feasible;
- G. no-T2 safety enforced export rule.

Each candidate must be compared against same-split nnU-Net for scar/edema Dice, HD95, component count, remote FP, no-T2 edema voxels, and label/export correctness. A MyoPS local candidate cannot be selected using foreground mean or empty-GT edema masking.

### H. Cine mandatory secondary: mature registration, not smoke/proxy

Cine is mandatory. M8 cannot skip Cine. It must run a mature multi-algorithm registration attempt, not a 3-case smoke or proxy-only path.

Registration minimum:

- at least 12 Cine cases or the maximum available same-safe subset;
- if fewer than 12 cases are available, write `CINE_RESOURCE_OR_DATA_BLOCKED` and list the available case pool;
- at least 3 non-reference frame pairs per case when frames allow; if not, write the per-case reason;
- at least two mature non-reference registration families from `heart_crop_center_of_mass_affine` or affine/translation initialization, `heart_crop_SimpleITK_Demons`, `heart_crop_SimpleITK_BSpline`, `ANTsPy_SyN_cropped_subset` if installed, and trained/auditable VoxelMorph only if weights/training evidence exists.

Optical flow or feature warp can be proxy evidence only; it cannot be the sole usable registration. Untrained VoxelMorph is never usable. One-case SyN is never usable.

For each algorithm on the same-safe subset, report before/after myocardium Dice, LV Dice, HD95, NCC, displacement smoothness/Jacobian/fold proxy, runtime, and failure reason. Select the best registration method using quantitative criteria.

Write `m8_cine_case_manifest.csv`, `m8_registration_same_subset_matrix.csv`, `m8_registration_method_selection.md`, and `m8_cine_decision.md`.

If no usable method remains after a mature attempt, write `CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT` and say whether this blocks M8 overall ready or only the Cine local candidate. Do not write `myocardium_cinemyops` ready.

### I. Cine temporal dictionary

If any usable non-reference registration row exists, M8 must execute temporal dictionary. Do not leave it blocked while retaining usable registration.

Temporal dictionary minimum: at least 3 cases with usable registration, or all usable cases if fewer exist; ED/reference anchor feature; at least 2 warped non-reference frame features per case; registration quality; frame quality; motion saliency; temporal representer slot usage; aggregation output; frame0 vs temporal same-case comparison; local class-1 myocardium Dice/HD95 proxy; class-3 sanity if available; hosted metric caveat.

Descriptor-only, frame0-only, no-warp, or optical-flow-only proxy temporal dictionary cannot be ready.

Write `m8_temporal_dictionary_evidence.csv`, `m8_temporal_dictionary_index.json`, `m8_temporal_dictionary_case_summary.csv`, `m8_temporal_aggregation_metrics.csv`, `m8_frame0_vs_temporal_help_harm.csv`, and `m8_cine_metrics_summary.csv`.

### J. Decision separation

Write `m8_myops_decision.md`, `m8_cine_decision.md`, and `m8_combined_decision.md`.

Rules: MyoPS local candidate does not automatically make Cine ready; Cine blocked does not erase useful MyoPS evidence, but M8 overall cannot be leaderboard-ready; if MyoPS has no promotion candidate, Cine diagnostics cannot create overall success; if Cine is skipped, M8 must fail; if Cine mature attempt is complete but fails, use `CINE_REGISTRATION_BLOCKED_AFTER_MATURE_M8_ATTEMPT` and do not claim `myocardium_cinemyops` ready.

### K. Official export / label-map dry run, no upload

M8 must not upload validation or create a validation package unless explicitly human-approved. It must still perform local export dry-run QC.

Write `m8_label_export_dry_run_qc.md` and `m8_official_label_mapping_qc.csv`. Check compact-to-official values: scar `2221`, edema `1220`, LV `500`, myocardium `200`, RV `600`; no missing class mismatch; no invalid label values; MyoPS and Cine branch output folder schema; zip/package not created unless human-approved; no validation upload or hosted metric claim.

### L. Strict monitor/completion and validator gate

M8 inherits `MONITOR_PACKET_IS_NOT_COMPLETION`.

- Pending/running Slurm jobs cannot receive normal review.
- Completed jobs must be re-aggregated into tracked lightweight evidence.
- `commands_run.md` with only `sbatch`, `squeue pending`, `PENDING Priority`, or `sacct pending` is not completion evidence.
- `M8_READY_FOR_REVIEW` must not contain unresolved `PENDING_MONITOR`, `NEEDS_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, `AWAITING_SACCT`, or equivalent states.

Implement or update `scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py`.

Known-bad fixtures must include total training budget under 8h marked ready; missing `m8_training_budget_ledger.csv`; pending monitor packet marked ready; completed job not re-aggregated; config contract not read by code; variants only renamed; missing per-case anchor delta; easy-only formal evaluation; no-T2 safety violation; missing local candidate assembly; Cine 3-case smoke/proxy-only registration; no best-registration selection; usable registration without temporal dictionary; missing label/export dry-run QC; real packet containing placeholder/synthetic-only final proof; unauthorized validation/upload/hosted claim.

Write `m8_strict_validator_report.md`, `m8_strict_validator_report.csv`, and `m8_validator_unit_test_report.md`. No `M8_READY_FOR_REVIEW` unless the validator passes on the real packet and fails closed on mutated known-bad fixtures.

### M. Required outputs

Write all outputs under `results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/`.

Required files: `result.md`, `completion_check.md`, `review_request.md`, `MANIFEST.md`, `commands_run.md`, `m8_route_objective.md`, `m8_training_budget_ledger.csv`, `m8_variant_config_contract.yaml` or `m8_variant_config_contract.json`, `m8_variant_matrix.csv`, `m8_architecture_gap_closure_table.csv`, `m8_hardcase_sampling_report.md`, `m8_batch_composition.csv`, `m8_prototype_bank_summary.json`, `m8_hard_negative_memory_summary.csv`, `m8_prototype_margin_by_case.csv`, `m8_proposal_refiner_recall_precision.csv`, `m8_loss_schedule.md`, `m8_training_curves.csv`, `m8_validation_events.csv`, `m8_loss_component_by_step.csv`, `m8_loss_component_gradient_sanity.csv`, `m8_srr_contribution_by_case.csv`, `m8_arbitration_opening_diagnostics.csv`, `m8_formal_case_manifest.csv`, `m8_same_split_help_harm.csv`, `m8_hard_subgroup_metrics.csv`, `m8_component_remote_fp_hd95_report.csv`, `m8_local_inference_recipe.md`, `m8_candidate_assembly_matrix.csv`, `m8_export_dry_run_qc.md`, `m8_best_variant_decision_table.csv`, `m8_route_promotion_decision.md`, `m8_cine_case_manifest.csv`, `m8_registration_same_subset_matrix.csv`, `m8_registration_method_selection.md`, `m8_temporal_dictionary_evidence.csv`, `m8_temporal_dictionary_index.json`, `m8_temporal_dictionary_case_summary.csv`, `m8_temporal_aggregation_metrics.csv`, `m8_frame0_vs_temporal_help_harm.csv`, `m8_cine_metrics_summary.csv`, `m8_myops_decision.md`, `m8_cine_decision.md`, `m8_combined_decision.md`, `m8_label_export_dry_run_qc.md`, `m8_official_label_mapping_qc.csv`, `m8_strict_validator_report.md`, `m8_strict_validator_report.csv`, `m8_validator_unit_test_report.md`, `m8_leaderboard_readiness_report.md`, and `m8_next_action.md`.

If a file is not applicable, it must exist and state `NOT_APPLICABLE_WITH_REASON`; this cannot bypass required MyoPS training budget, real config use, broad formal evidence, per-case contribution export, local candidate assembly, mature Cine registration, temporal dictionary when usable registration exists, label/export dry-run QC, or strict validator.

### N. Completion states

`completion_check.md` may contain only:

- `M8_READY_FOR_REVIEW`
- `M8_NEEDS_MONITOR_NO_REVIEW`
- `M8_RESOURCE_BLOCKED`
- `M8_NEEDS_REVISION_TRAINING_UNDERRUN`
- `M8_NEEDS_REVISION_ARCHITECTURE_GAP`
- `M8_NEEDS_EVIDENCE_UNDERTRAINED`
- `M8_NEEDS_EVIDENCE_METRICS_INCOMPLETE`
- `M8_NEEDS_EVIDENCE_CINE_REGISTRATION`
- `M8_NEEDS_REVISION`
- `M8_BLOCKED_BY_M7`

Do not write `M8_READY_FOR_REVIEW` if total MyoPS training loop seconds are below `28800` without resource/user exception; `m8_training_budget_ledger.csv` is missing or does not prove the budget; any formal decision training/probe is only a few-minute smoke; variant config contract is missing or not used by code; variants only differ by name; architecture gaps remain `NEEDS_REVISION` or `NEEDS_EVIDENCE`; `m8_srr_contribution_by_case.csv` lacks per-case delta/contribution export; hardcase sampler lacks per-step evidence; local inference recipe or candidate assembly is missing; official label/export dry-run QC is missing; Cine mature multi-algorithm registration attempt is missing; usable Cine registration exists but temporal dictionary is not executed; monitor/pending/submitted-only evidence is present; this M8 prompt is not merged into shared executor/reviewer prompts; any placeholder, stale, synthetic-only, or table-only evidence is used as final M8 proof; validation packaging/upload, hosted metric claim, fold expansion, challenge submission, scientific stop, leaderboard readiness, challenge-ready status, or M9 is claimed.

Finish by force-adding and locally committing only lightweight evidence plus necessary first-party helper/source/test files. Do not commit checkpoints, NIfTI predictions, upload packages, raw data, secrets, environment dumps, whole runtime trees, or large logs. Do not write `review.md`. Do not push.
```

## M8 executor follow-up: no-promotion repair decision

You are the Codex executor/controller for exactly one post-M8 follow-up milestone. This is not M9, not fold expansion, not validation packaging, and not route promotion.

Required protocol sentence: This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md, force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.

### 1. Required reading before execution

Read these files before doing any scientific or code work:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/result.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/completion_check.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/MANIFEST.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/commands_run.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_route_promotion_decision.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_best_variant_decision_table.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_candidate_assembly_matrix.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_same_split_help_harm.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_srr_contribution_by_case.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_hard_subgroup_metrics.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_component_remote_fp_hd95_report.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_nnunet_anchor_control_metrics.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_training_budget_ledger.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_validation_events.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_temporal_dictionary_evidence.csv
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/m8_registration_same_subset_matrix.csv
```

If any required M8 evidence file is missing, write a minimal blocked packet with status `M8_FOLLOWUP_NEEDS_EVIDENCE_MISSING_M8_INPUT`, list the missing paths, and stop. Do not infer from old summaries.

### 2. Task identity and scope

Use this result directory:

```text
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/
```

Allowed first-party helper path:

```text
scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py
```

The scientific question is narrow:

Can existing M8 evidence support a deployable, non-GT, non-case-ID, baseline-preserving arbitration or repair contract that makes SRR-v3 useful after the M8 no-promotion review, or must GPT return to route planning because the current SRR candidate family is still scientifically unresolved?

This follow-up must use existing M8 evidence and, if available locally, existing M8 runtime prediction/proxy artifacts. It must not start new model training. It must not submit validation packaging. It must not upload. It must not claim hosted metrics. It must not turn M8 into M9.

### 3. Route interpretation to enforce

The follow-up must preserve the SRR-v3 route structure:

1. availability-aware modality handling; zero-filled missing C0/T2 must never be interpreted as real images without an availability mask;
2. semantic representation retrieval and prototype/dictionary evidence must be connected to final logits or final labels, not only CSV diagnostics;
3. anatomy-guided proposal must remain soft and evidence-based; no hard deletion or hard ROI clipping as the mainline;
4. scar and edema must be evaluated separately, with pathology-specific failure modes and no `foreground_mean` promotion;
5. no-T2 edema safety is mandatory: no rule may treat no-T2 myocardium as edema-negative training evidence, and no deployable arbitration may introduce edema voxels into no-T2 safety cases;
6. nnU-Net may be the anchor/control and safety source, but SRR cannot be reduced to an optional postprocess wrapper.

### 4. Required implementation or diagnostic work

Implement or update `scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py` so it can be run from repository root and produce a fail-closed result packet. It may read tracked M8 CSV/JSON/MD evidence and local runtime summaries if present. It must not require checkpoints or NIfTI files to pass the minimal diagnostic, but if local prediction artifacts are available it may add optional final-label-impact checks.

The helper must construct four ledgers:

1. `m8_review_findings_ledger.csv`: parse or manually encode M8 review claims into machine-checkable rows with fields `finding_id`, `source_path`, `source_line_or_section`, `claim`, `effect_on_followup`, `blocking_level`.
2. `m8_candidate_failure_matrix.csv`: summarize why each M8 candidate failed promotion. Required fields: `candidate_id`, `metric_name`, `anchor_dice`, `candidate_dice`, `dice_delta`, `anchor_hd95`, `candidate_hd95`, `hd95_delta`, `remote_fp_delta`, `component_delta`, `hard_subgroup`, `failure_class`, `eligible_for_repair_contract`.
3. `m8_proxy_feature_schema.csv`: define deployable proxy features allowed for arbitration. Required fields: `feature_name`, `source`, `available_at_inference`, `uses_ground_truth`, `uses_case_id`, `uses_hosted_feedback`, `allowed_for_policy`, `reason`.
4. `m8_proxy_arbitration_help_harm.csv`: evaluate at least three pre-declared deployable policies against the nnU-Net anchor and M8 candidates. Required fields: `policy_id`, `policy_description`, `uses_only_allowed_features`, `candidate_source`, `metric_name`, `case_count`, `dice_mean_anchor`, `dice_mean_policy`, `dice_delta`, `hd95_mean_anchor`, `hd95_mean_policy`, `hd95_delta`, `remote_fp_mean_anchor`, `remote_fp_mean_policy`, `no_t2_edema_voxels`, `scar_guardrail_status`, `edema_guardrail_status`, `promotion_status`.

The three policy families must include:

1. `anchor_only_control`: the no-change safety baseline;
2. `candidate_only_control`: the best M8 local candidate as-is, to verify the M8 no-promotion result is reproduced;
3. at least one deployable arbitration/fallback policy that may use only non-GT proxy signals such as availability mask, T2-present status, residual magnitude, candidate-anchor disagreement magnitude, distance to anatomy support, component size, largest-component fraction, baseline/candidate uncertainty if already exported, proposal/refiner gate statistics if already exported, and local intensity/prototype support if already exported.

Forbidden policy features:

```text
case_id
validation ground truth labels for choosing the rule
Dice / HD95 / component metric values as rule inputs
hosted validation feedback
manual case lists
center ID as a primary decision feature unless explicitly marked diagnostic-only
empty-GT shortcut promotion
foreground_mean-only selection
```

Ground truth may be used only after a policy is pre-declared, to evaluate help/harm on the same split. If thresholds are tuned using metrics, the helper must label the result `DIAGNOSTIC_THRESHOLD_TUNED_NOT_DEPLOYABLE` and must not mark it repair-ready.

Additional repair-contract readiness constraint: when executing the M8 follow-up prompt, treat a policy as diagnostic-only, not repair-contract-ready, if its benefit comes mainly from anchor-only fallback, uses SRR on only a negligible fraction of cases, improves only a single easy metric while leaving edema/remote-FP/component hard subgroups unresolved, or cannot explain why the deployable proxy selects SRR in terms of the SRR-v3 mechanism. A valid repair contract must show that SRR contributes a nontrivial, mechanism-consistent, same-split help signal under allowed non-GT proxy features; otherwise choose `GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR`.

### 5. Required outputs

The result directory must contain these top-level files:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m8_followup_route_objective.md
m8_review_findings_ledger.csv
m8_candidate_failure_matrix.csv
m8_proxy_feature_schema.csv
m8_proxy_arbitration_help_harm.csv
m8_hard_subgroup_help_harm.csv
m8_no_t2_safety_report.csv
m8_repair_contract.md
m8_next_required_action.md
m8_followup_strict_validator_report.csv
m8_followup_strict_validator_report.md
m8_followup_validator_selftest_report.csv
m8_followup_validator_selftest_report.md
```

`m8_followup_route_objective.md` must restate that the objective is post-M8 no-promotion repair decision, not M9, not route promotion, and not validation packaging.

`m8_hard_subgroup_help_harm.csv` must include at least these subgroup labels when present in M8 evidence: `CenterB`, `CenterC`, `T2_present`, `no_T2_safety`, `scar_positive`, `edema_positive`, `remote_FP_cases`, and `component_burden_cases`.

`m8_no_t2_safety_report.csv` must explicitly report whether any policy introduces edema voxels for no-T2 cases. Any nonzero value is a blocker unless the row is explicitly diagnostic-only and not selected.

`m8_repair_contract.md` must state one of:

```text
REPAIR_CONTRACT_READY_FOR_REVIEW
NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND
NEEDS_EVIDENCE_MISSING_INPUTS
NEEDS_REVISION_PIPELINE_OR_VALIDATOR
```

A repair contract can be marked ready only if it is deployable, uses no forbidden features, preserves no-T2 edema safety, is compared to the same-split nnU-Net anchor, reports scar and edema separately, includes hard-subgroup help/harm, and does not claim validation readiness. It may authorize GPT to consider a future bounded implementation milestone; it does not authorize Codex to start that milestone.

`m8_next_required_action.md` must choose exactly one next action:

```text
GPT_PLAN_BOUNDED_REPAIR_IMPLEMENTATION
GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR
NEEDS_EVIDENCE_BEFORE_ANY_NEXT_TASK
NEEDS_REVISION_BEFORE_REVIEW
```

### 6. Strict validator and known-bad self-tests

The helper or separate validator mode must fail closed on these known-bad mutations:

1. missing M8 review or wrong previous token;
2. missing same-split nnU-Net anchor comparison;
3. policy uses `case_id`;
4. policy uses Dice/HD95/component values as decision inputs;
5. policy uses hosted feedback;
6. no-T2 edema voxels are introduced by a selected policy;
7. only `foreground_mean` is reported;
8. candidate-only is marked promoted despite M8 no-promotion review;
9. required output missing;
10. `completion_check.md` says ready while validator has nonzero errors;
11. route promotion, fold expansion, validation packaging, upload, hosted metric claim, or M9 is claimed;
12. monitor or pending Slurm status is marked completion;
13. Cine frame0-only or descriptor-only evidence is used to claim temporal readiness;
14. synthetic or placeholder evidence is used as the only proof.

The self-test report must include at least one good fixture and the known-bad mutations above. If any known-bad mutation passes, completion must be `M8_FOLLOWUP_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

### 7. Completion states

Allowed executor completion states:

```text
M8_FOLLOWUP_READY_FOR_REVIEW
M8_FOLLOWUP_NEEDS_EVIDENCE_MISSING_M8_INPUT
M8_FOLLOWUP_NEEDS_REVISION_PIPELINE_OR_VALIDATOR
M8_FOLLOWUP_NO_DEPLOYABLE_REPAIR_FOUND_READY_FOR_REVIEW
M8_FOLLOWUP_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

`M8_FOLLOWUP_READY_FOR_REVIEW` is allowed only when all required files exist, the validator exits zero on the real packet, known-bad self-tests fail closed, and no forbidden action is claimed. It is not an audited decision.

### 8. Git and artifact policy

Commit only lightweight Markdown/CSV/JSON files and the first-party helper. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees.

Recommended local commit command:

```bash
git add -f scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py \
  results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/*.md \
  results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/*.csv \
  results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/*.json
git commit -m "Add M8 follow-up repair decision packet"
```

Do not push automatically.

# M9 SRR Dictionary Fidelity Repair + Pathology-specific Refiner + Cine Final-output Training Evidence

This canonical shared prompt was merged from the GPT-authored M9 staging files and those staging files were deleted after merge verification.

This section is intentionally a milestone prompt, not a result packet and not a route-promotion claim. It does not authorize validation packaging, validation upload, hosted metric claims, leaderboard claims, fold expansion, scientific stop, or M10.

## Route Bootstrap Evidence

```yaml
diagram_source: "current conversation uploaded visual materials / ChatGPT visual channel"
diagram_versions_read: ["SRR-v2", "SRR-v2.5", "SRR-v3"]
canonical_repo_paths: ["images/SRR-v2.png", "images/SRR-v2.5.png", "images/SRR-v3.png"]
visual_read_status: "READ_FROM_CURRENT_CONVERSATION_UPLOADS"
previous_m8_review_path: "results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md"
previous_m8_review_token: "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
previous_followup_review_path: "results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md"
previous_followup_review_token: "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED"
source_todo: "TODO.md"
source_dictionary_todo: "TODO-dictionary.md"
source_paper_local: "Representation Retrieval Learning for Heterogeneous Data Integration.pdf"
merged_into: "prompts/shared/EXECUTOR_PROMPTS.md and prompts/shared/REVIEWER_PROMPTS.md"
```

Recovered route objective: SRR-MyoPS is a primary availability-aware selective representation retrieval system for medical imaging, not an nnU-Net postprocess. The key research claim is that a Blockwise Representation Retrieval-style dictionary can be adapted from heterogeneous tabular/multi-source learning into multi-modal CMR segmentation by using real modality-specific image encoders, source/availability-aware representer retrieval, pathology-specific lesion proposal dictionaries, pattern-SIP regularization, anatomy-guided soft ROI refinement, safe negative-space learning, and final output evidence where SRR is the primary lesion-evidence generator. nnU-Net may be used only as context, teacher, uncertainty feature, safety source, and same-split control. It must not be the normal final-logit anchor for candidate models.

The diagrams explicitly distinguish scar and edema. Scar is LGE-dominant, typically smaller/focal, and needs a small-ROI high-resolution precision refiner that reduces remote false positives and HD95 while preserving small lesions. Edema is T2-conditioned, more spatially diffuse/contextual, and needs a larger-ROI context-preserving refiner that improves T2-present edema recall/HD95 without ever treating no-T2 cases as edema negatives. A shared generic pathology refiner, or a refiner that only changes a class label string while using the same ROI/crop/loss/gate behavior for scar and edema, is not faithful to the route diagrams.

Cine remains the secondary line, but it is not optional future work. The Cine branch in the diagrams is registration-aware anatomy-first temporal retrieval: cine sequence -> ED/reference anchor + selected key frames -> frame quality / motion-saliency router -> reference-frame registration / warping -> temporal representation dictionary -> frame-wise anatomy prior + temporal aggregation -> final myocardium_cinemyops output. M9 must therefore include a real Cine final-output branch on a local/safe subset. CineMA or any local frame-wise anatomy model may be a backbone/context source, but downloading weights, listing provenance, running one SyN/Demons smoke, or producing descriptor-only evidence is not completion.

The R2 / BR2 paper basis to preserve in this milestone:

1. R2 learns a shared representer dictionary `Theta = {theta_1, ..., theta_D}` and source/task-specific sparse retrieval coefficients `beta^(s)` so each source retrieves a relevant subset of representers.
2. Integrativeness is the number of sources that retrieve a representer, `gamma_d = sum_s I(beta_d^(s) != 0)`.
3. SIP encourages integrative representers instead of forcing either full sharing or isolated per-source experts.
4. BR2 handles blockwise missingness by using modality-specific dictionaries `Theta_m`, observed-modality indicators `I_m^(s)`, and no imputation. Missing modalities must contribute zero by construction, not by fake zero-filled images.
5. For medical imaging, the natural extension is pattern-conditioned dictionary retrieval across availability groups, centers/styles, hard subgroups, and lesion contexts; dictionary usefulness must be proven by final-logit/final-label causal effect, not by slot names or diagnostic CSVs alone.

M8 / M8 follow-up scientific state: current M8 candidate family is `NO_PROMOTION`; M8 follow-up found `NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND`; neither packet scientifically disproves SRR. They show that the current implementation is too anchor-centered, loss-weight wiring is suspect, checkpoint selection is not metric-aligned, prototype memory is not strong enough, scar/edema refiners are not yet proven as distinct lesion formation modules, and Cine evidence is proxy-only. M9 is therefore a fidelity-repair-plus-training milestone with a required Cine final-output branch, not a route abandonment milestone.

## M9 executor: SRR dictionary fidelity repair + pathology-specific refiner + Cine final-output training evidence


You are the Codex executor/controller for exactly one milestone: M9 SRR dictionary fidelity repair + pathology-specific refiner + Cine final-output training evidence. This is a high-risk CARE model implementation milestone. It is not fold expansion, not validation packaging, not validation upload, not route promotion, and not M10.

Required protocol sentence: This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md, force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not start the next milestone. The milestone must be reviewed by a separate read-only Codex session before continuation.

Before executing the scientific task, enforce the hard-gate policy: exact task graph, strict validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, and SRR diagram-bootstrap evidence when the task touches SRR/MyoPS/Cine route planning. If any hard gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE; do not continue to final audit.

### 1. Required reading before execution

Read these files before editing code or running training:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
TODO.md
TODO-dictionary.md
results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint/review.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/review.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_repair_contract.md
results/20260708_srr_v3_m8_followup_no_promotion_repair_decision/m8_next_required_action.md
prompts/tasks/20260703_cine_motion.md
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/losses/srr_losses.py
scripts/training/run_srr_propref_myops_fold0.py
scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py
```

If any required M8 or M8 follow-up review file is missing, write a blocked packet with status `M9_NEEDS_EVIDENCE_MISSING_PREREQUISITE_REVIEW` and stop. Do not infer from chat summaries.

If this milestone will submit any Slurm job, also read and apply:

```text
.agents/skills/slurm-routing-partition/SKILL.md
```

### 2. Task identity and result directory

Use this result directory:

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/
```

Allowed first-party code paths:

```text
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/models/proposal_prototypes.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/losses/srr_losses.py
src/care_myocardium/cine/
scripts/training/run_srr_propref_myops_fold0.py
scripts/training/run_cine_temporal_output_m9.py
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
jobs/src/run_srr_v3_m9_dictionary_fidelity_training_htzhulab.sh
jobs/src/run_srr_v3_m9_dictionary_fidelity_training.sh
jobs/src/run_srr_v3_m9_cine_temporal_output_htzhulab.sh
jobs/src/run_srr_v3_m9_cine_temporal_output.sh
```

You may add small unit tests under an appropriate first-party test path if the repo already has a test convention. If no test convention exists, place validator self-tests inside the M9 validator and report them in result files.

### 3. Scientific goal

M9 must answer two questions:

1. After repairing implementation fidelity, does a true BR2-inspired SRR dictionary system produce stable lesion-evidence improvement over current M8-style anchor-residual behavior, especially for T2-present edema-positive CenterB/CenterC cases, while preserving scar and no-T2 safety?
2. Can the Cine secondary branch be advanced from proxy evidence to a real local final-output model/pipeline that uses non-reference cine frames through registration/warping or temporal feature aggregation and produces `myocardium_cinemyops` predictions on a safe local subset?

Do not answer either question by claiming a leaderboard result. Answer by code fidelity checks, causal ablations, M8-equivalent training evidence, same-split metrics, hard-subgroup metrics, local final-output Cine metrics, and independent review.

### 4. Non-negotiable design constraints

nnU-Net must not be the main model in M9 candidate outputs. It is allowed only as:

```text
same_split_control
context_feature
teacher_feature
uncertainty_feature
safety_fallback_for_explicit_failure_cases
anatomy/context source when explicitly tagged
```

Forbidden for M9 candidate outputs:

```text
final_logits = nnunet_anchor_logits + bounded_srr_delta
normal output path uses anchor logits as the base logits
candidate selected because it preserves anchor identity
route promotion based on anchor-only or foreground_mean
silent fallback to nnU-Net
hidden nnU-Net identity under SRR naming
```

A separate `anchor_only_control` and an `m8_anchor_residual_control` are required as controls. They may not be selected as SRR route candidates.

Cine is not allowed to be skipped as "optional future work." A missing Cine final-output branch is a M9 blocker unless the result packet honestly returns `M9_NEEDS_EVIDENCE` or `M9_RESOURCE_BLOCKED` with exact missing files/dependencies and no scientific claim.

### 5. Required repairs

#### 5.1 Loss-weight wiring repair

Fix the M8/M9 loss contract bug: variant-specific JSON or CLI loss weights must actually enter `srr_m6_expanded_total_loss(...)` or its M9 replacement. The repair must support explicit weights for at least:

```text
loss_anatomy_union_lv_rv
loss_scar_proposal
loss_edema_proposal_t2_present_only
loss_scar_refiner_small_roi
loss_edema_refiner_large_roi_t2_present
loss_anchor_preservation_outside_roi
loss_correction_opportunity
loss_branch_arbitration_consistency
loss_bounded_correction
loss_component_remote_fp
loss_no_t2_edema_safety
loss_dictionary_entropy_coverage_load_balance
loss_pattern_sip_integrativeness
loss_prototype_diversity_margin
loss_memory_bank_update_or_alignment
loss_refiner_final_label_effect
loss_cine_temporal_consistency
loss_cine_reference_warp_consistency
```

Required proof: a unit/validator test must set a component weight to `0` and a large value such as `10`, then prove that total loss and at least one relevant gradient norm change. If this test is missing, M9 must be `NEEDS_REVISION`.

#### 5.2 Metric-aligned checkpoint selection repair

Stop selecting best checkpoint by patch loss alone. Patch loss may remain a sanity metric. For formal M9 candidates, scheduled checkpoints must be evaluated on a bounded same-split validation subset and best selection must use metric-facing fields:

```text
scar Dice
scar HD95
scar remote-FP count
scar component count
scar small-ROI refiner precision / recall
edema Dice on T2-present edema-positive cases
edema HD95 on T2-present edema-positive cases
edema remote-FP count
edema component count
edema large-ROI coverage / false-positive ratio
CenterB / CenterC subgroup help-harm
no-T2 edema safety
```

The selected checkpoint must be recorded in `m9_metric_aligned_checkpoint_selection.csv`. If GPU budget prevents full-volume evaluation at every checkpoint, evaluate at a fixed schedule and document the exact cases and cost. Do not select by `val_patch_loss` alone.

#### 5.3 SRR-main final-output repair

Add a formal M9 candidate mode where SRR, proposal, and refiner logits are the primary final evidence. In this mode nnU-Net may enter as context/teacher/safety features but not as final-logit base. The model must expose:

```text
m9_final_output_mode: SRR_MAIN_NOT_ANCHOR_RESIDUAL
nnunet_role: CONTEXT_TEACHER_SAFETY_CONTROL_ONLY
srr_main_logits
proposal_logits
refiner_logits
anatomy_context_logits
final_logits
final_label_delta_vs_srr_without_dictionary
final_label_delta_vs_anchor_control
```

You may preserve an explicit safety fallback branch only for diagnostic rows. If a candidate mostly collapses to fallback, it must be labeled `FALLBACK_DOMINATED_NOT_SRR_MAIN`.

#### 5.4 True-BR2 modality dictionary repair

Implement a true BR2 medical-imaging dictionary path. It must prohibit `[fused, fused, fused]` pseudo-modality input for formal M9 candidates. Each scale dictionary must consume real per-modality features:

```text
LGE_scale_l
T2_scale_l when T2 is available
C0_scale_l when C0 is available
```

Required dictionary families:

```text
shared dictionary D_l^shared
LGE private dictionary D_l^LGE
T2 private dictionary D_l^T2
C0 private dictionary D_l^C0
LGE-T2 interaction dictionary D_l^{LGE,T2}
LGE-C0 interaction dictionary D_l^{LGE,C0}
optional T2-C0 interaction dictionary D_l^{T2,C0} only when justified
```

Invalid missing-modality slots must be masked before routing. Interaction slots must be unavailable unless all modalities in the pair are present.

#### 5.5 Pattern-SIP / integrativeness repair

Implement a differentiable medical-imaging adaptation of SIP. It should not merely force uniform gate coverage. It must estimate soft integrativeness by task, slot, and pattern group:

```text
u_{task, slot, group} = mean gate usage for task/slot over group
```

Pattern groups must include, when available:

```text
availability pattern: LGE-only, C0+LGE, C0+LGE+T2
center/style group: CenterA/CenterB/CenterC or documented available centers
pathology group: scar-positive, edema-positive, empty-GT
hard subgroup: remote-FP, component-burden, T2-present edema-positive
```

The M9 pattern-SIP objective should encourage true shared slots to have stable usage across multiple compatible groups, encourage LGE-private slots for scar evidence, T2-private / LGE-T2 interaction slots for edema evidence when T2 is present, and avoid invalid slot usage. It must report:

```text
m9_pattern_sip_usage_by_group.csv
m9_integrativeness_gamma_soft.csv
m9_dictionary_slot_group_stability.csv
m9_dictionary_invalid_slot_mask_report.csv
```

#### 5.6 Prototype / memory repair

Replace or augment fixed-buffer prototypes with a stronger auditable prototype memory. Acceptable implementations:

```text
learnable prototype parameters initialized from same-split train/OOF features
or EMA prototype buffers updated from train features with explicit update ledger
or a hybrid: fitted prototypes plus learnable projection and EMA category means
```

The memory must separately track scar-positive, scar-safe-negative, edema-positive, and edema-safe-negative categories. Edema negatives must be T2-present only. no-T2 myocardium must never enter edema negative memory.

Required evidence:

```text
m9_prototype_memory_summary.json
m9_prototype_update_ledger.csv
m9_hard_negative_replay_ledger.csv
m9_no_t2_edema_negative_violation_report.csv
```

If any formal candidate still uses deterministic axis prototypes as the only prototype source, mark it `DETERMINISTIC_BOOTSTRAP_NOT_FORMAL` and do not use it for route decisions.

#### 5.7 Lesion proposal dictionary and T2-present edema recall repair

M9 must prioritize lesion formation, not just evidence selection. For scar and edema proposal dictionaries, report proposal recall/precision and lesion-wise recall before final mask evaluation.

Required for edema:

```text
T2-present edema-positive proposal recall
CenterB edema proposal recall
CenterC edema proposal recall
edema HD95 and component count on T2-present edema-positive subset
no-T2 edema blocked logits and export safety
```

Training must stratify or oversample T2-present edema-positive cases, especially CenterB/CenterC, without turning no-T2 cases into edema negatives.

#### 5.8 Pathology-specific refiner asymmetry repair

This is a hard requirement from the SRR diagrams. Scar and edema must not share a generic refiner disguised by different class names.

Implement or verify separate refiner behavior:

```text
scar_refiner:
  objective: focal scar localization, small-ROI high-resolution correction
  dominant_modality: LGE
  roi_policy: small ROI / tighter crop / high precision
  safety_target: reduce remote FP and HD95, preserve small true lesions
  evidence_inputs: scar proposal, scar prototype similarity, LGE crop, anatomy prior, uncertainty, scar component context
  required_metrics: small lesion recall, scar proposal precision, scar HD95, scar remote-FP, final-label delta

edema_refiner:
  objective: diffuse/contextual edema refinement, large-ROI context-preserving correction
  dominant_modality: T2 when present
  roi_policy: larger ROI / broader crop / context preserving
  safety_target: improve T2-present edema recall and HD95 without no-T2 edema leakage
  evidence_inputs: edema proposal, edema prototype similarity, T2 crop, anatomy prior, uncertainty, edema component context
  required_metrics: T2-present edema proposal recall, CenterB/CenterC edema Dice/HD95, component count, no-T2 safety
```

Required outputs:

```text
m9_pathology_specific_refiner_contract.md
m9_scar_refiner_roi_stats.csv
m9_edema_refiner_roi_stats.csv
m9_refiner_asymmetry_ablation.csv
```

The validator must fail if scar and edema use identical crop sizes, identical ROI thresholds, identical modality inputs, identical loss weights, and identical reported success criteria in a formal candidate. Shared helper code is allowed only if the actual instantiated behavior is pathology-specific and auditable.

#### 5.9 Refiner causal-effect repair

The refiner must prove it changes final logits/final labels in a useful way, not only produce residual tensors. Required ablations:

```text
SRR-main without refiner
SRR-main with proposal only
SRR-main with proposal + scar small-ROI refiner
SRR-main with proposal + edema large-ROI refiner
SRR-main with both pathology-specific refiners
SRR-main with dictionary disabled
SRR-main with pattern-SIP disabled
M8 anchor-residual control
anchor-only control
```

For each ablation, report final-label delta, Dice/HD95/component/remote-FP, hard-subgroup help/harm, and scar/edema separate refiner effect. The refiner is not considered implemented for scientific purposes unless it changes final labels on at least one nontrivial scar or edema-positive case and does not violate no-T2 safety.

#### 5.10 Cine final-output branch: required secondary line, not optional

M9 must implement a real local Cine final-output branch or honestly block. It cannot stop at weight download, provenance listing, single SyN/Demons smoke, descriptor-only temporal retrieval, or frame0-only output.

Minimum architecture:

```text
Cine input sequence
-> ED/reference selection contract
-> frame quality / motion saliency router
-> frame-wise anatomy backbone or local CineMA/adapter feature source with license/provenance
-> non-reference frame registration / warping OR feature-level temporal alignment
-> temporal representation dictionary with frame-quality and motion-saliency slots
-> temporal aggregation / anatomy prior fusion
-> final compact label prediction for myocardium_cinemyops local safe subset
-> local same-subset metrics vs frame0/reference and existing local controls
```

Allowed implementation modes:

```text
mode_A_registration_temporal_dictionary:
  use frame-wise CineMA/local anatomy predictions as anatomy evidence
  register selected non-reference frames to reference
  build temporal dictionary from reference + warped non-reference evidence
  aggregate to final myocardium_cinemyops prediction

mode_B_feature_temporal_output_model:
  encode reference and selected non-reference frames
  use motion saliency / frame quality router
  aggregate features through temporal representation dictionary
  decode final myocardium_cinemyops mask

mode_C_anatomy_first_temporal_adapter:
  use local CineMA/CorSeg-like frame-wise anatomy outputs if already available
  train or calibrate a first-party temporal adapter on local train/safe split
  output final compact labels and compare against frame0-only control
```

Forbidden Cine completions:

```text
downloaded weights only
license/provenance only
frame0-only output marked temporal
descriptor CSV without final prediction
single-case or near-single-case SyN/Demons smoke
untrained or unverified VoxelMorph claim
registration metrics without temporal aggregation
temporal dictionary without final output labels
final output without local same-subset comparison to frame0/reference control
validation package or upload
```

Required Cine outputs:

```text
m9_cine_architecture_contract.md
m9_cine_weight_provenance.md
m9_cine_reference_frame_contract.md
m9_cine_final_output_manifest.csv
m9_cine_final_output_qc.md
m9_cine_registration_quality.csv
m9_cine_temporal_dictionary_usage.csv
m9_cine_temporal_case_metrics.csv
m9_cine_frame0_vs_temporal_help_harm.csv
m9_cine_failure_matrix.csv
m9_cine_next_required_action.md
```

Cine runtime NIfTI predictions may be written under ignored runtime directories for local evaluation, but do not commit NIfTI files. Commit only lightweight metrics/QC/manifest files.

If no local CineMA/Cine anatomy artifacts are available, do not download weights. Either use existing local frame-wise predictions if present and record provenance, or write `M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING`. Missing Cine evidence is not permission to skip Cine while marking MyoPS M9 ready; the completion state must reflect the blocker.

### 6. Required M9 variants and controls

Formal MyoPS M9 must include at least these candidate/control families:

```text
anchor_only_control
m8_anchor_residual_control
m9_srr_main_true_br2_pattern_sip
m9_srr_main_lesion_proposal_memory
m9_srr_main_t2_edema_recall_focus
```

Minimum causal ablations may be done by toggles or separate runs, but the result packet must include their metric rows:

```text
no_dictionary
no_pattern_sip
no_prototype_memory
no_refiner
scar_refiner_only
edema_refiner_only
proposal_only
refiner_enabled
```

The controls are mandatory for interpretation but cannot be promoted.

Formal Cine M9 must include at least:

```text
cine_reference_frame_control
cine_framewise_cinema_or_local_anatomy_control
cine_registration_temporal_dictionary_output
cine_temporal_output_model_or_adapter
```

If a Cine variant is blocked, the result must include exact blocker, missing files/dependencies, and next required action. Do not silently mark it optional.

### 7. Minimum training budget and runtime rules

M9 must include M8-like MyoPS training evidence, not just smoke. Minimum formal MyoPS budget:

```text
aggregate_train_loop_seconds >= 28800 OR at least three formal SRR-main candidates with >= 7200 train_loop_seconds each plus one control eval
min_optimizer_steps_per_formal_candidate >= 6000 unless train_loop_seconds >= 7200 and loss plateau is documented
validation_event_count_per_formal_candidate >= 20
one_batch_overfit required
loss decrease required
prediction sanity required
same-split anchor/control metrics required
hard subgroup metrics required
```

M9 must also include Cine final-output evidence. Minimum formal Cine evidence:

```text
safe local case count >= 12 when available, otherwise all available safe cases with blocker if < 8
at least one non-reference frame per evaluated case when available
frame0/reference control comparison required
final compact-label output required
temporal aggregation output required
registration/warp or feature-alignment sanity required
component/HD95/volume or documented local proxy metrics required
```

If a Cine temporal head is trained, use a bounded job with max 8 hours and report optimizer steps, loss, validation events, and final-output metrics. If using a deterministic temporal aggregation pipeline first, it must still produce final predictions and metrics; do not call it a trained model.

If scheduler or runtime blocks training, write `M9_NEEDS_MONITOR` or `M9_RESOURCE_BLOCKED` as appropriate. A monitor packet is not completion.

Training must produce stable loss and metrics. If loss is NaN/Inf, detached, non-decreasing without explanation, or if required loss components have zero gradient without a valid mask reason, M9 must be `NEEDS_REVISION` or `SCIENTIFIC_UNDERTRAINED`, not ready.

### 8. Required outputs

The result directory must contain at least:

```text
result.md
completion_check.md
review_request.md
MANIFEST.md
commands_run.md
m9_route_objective.md
m9_rrl_brr2_adaptation_contract.md
m9_dictionary_fidelity_matrix.csv
m9_code_patch_summary.md
m9_loss_weight_wiring_test_report.md
m9_metric_aligned_checkpoint_selection.csv
m9_nnunet_role_audit.md
m9_pattern_sip_usage_by_group.csv
m9_integrativeness_gamma_soft.csv
m9_dictionary_slot_group_stability.csv
m9_dictionary_invalid_slot_mask_report.csv
m9_prototype_memory_summary.json
m9_prototype_update_ledger.csv
m9_hard_negative_replay_ledger.csv
m9_no_t2_edema_negative_violation_report.csv
m9_pathology_specific_refiner_contract.md
m9_scar_refiner_roi_stats.csv
m9_edema_refiner_roi_stats.csv
m9_refiner_asymmetry_ablation.csv
m9_training_budget_ledger.csv
m9_training_curves.csv
m9_validation_events.csv
m9_loss_component_gradient_sanity.csv
m9_candidate_assembly_matrix.csv
m9_same_split_help_harm.csv
m9_hard_subgroup_metrics.csv
m9_component_remote_fp_hd95_report.csv
m9_proposal_refiner_recall_precision.csv
m9_refiner_causal_effect.csv
m9_ablation_matrix.csv
m9_cine_architecture_contract.md
m9_cine_weight_provenance.md
m9_cine_reference_frame_contract.md
m9_cine_final_output_manifest.csv
m9_cine_final_output_qc.md
m9_cine_registration_quality.csv
m9_cine_temporal_dictionary_usage.csv
m9_cine_temporal_case_metrics.csv
m9_cine_frame0_vs_temporal_help_harm.csv
m9_cine_failure_matrix.csv
m9_cine_next_required_action.md
m9_route_promotion_decision.md
m9_next_required_action.md
m9_strict_validator_report.csv
m9_strict_validator_report.md
m9_validator_selftest_report.csv
m9_validator_selftest_report.md
```

`m9_route_promotion_decision.md` may state only one of:

```text
M9_NO_PROMOTION_DIAGNOSTIC_ONLY
M9_REPAIR_CONTRACT_READY_FOR_REVIEW
M9_NEEDS_EVIDENCE
M9_NEEDS_REVISION
M9_SCIENTIFIC_UNDERTRAINED
M9_NEEDS_MONITOR
M9_RESOURCE_BLOCKED
```

`M9_REPAIR_CONTRACT_READY_FOR_REVIEW` means only that an independent reviewer may consider whether GPT can plan M10. It does not authorize validation packaging/upload, hosted metric claims, leaderboard claims, fold expansion, or scientific stop.

`m9_next_required_action.md` must choose exactly one:

```text
GPT_PLAN_M10_DICTIONARY_ITERATION
GPT_PLAN_M10_CINE_TEMPORAL_ROUTE
GPT_PLAN_M10_DICTIONARY_AND_CINE_EXPANSION
GPT_REPLAN_AFTER_M9_NO_PROMOTION
NEEDS_EVIDENCE_BEFORE_NEXT_TASK
NEEDS_REVISION_BEFORE_REVIEW
NEEDS_MONITOR
```

### 9. Strict validator and known-bad self-tests

Implement `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py`. It must fail closed on at least these mutations:

1. missing M8 follow-up review token;
2. missing diagram bootstrap fields;
3. missing required output file;
4. loss-weight wiring test absent or does not prove total loss/gradient changes;
5. checkpoint selected by patch loss only;
6. formal candidate uses `final_logits = nnunet_anchor_logits + bounded_delta` as normal output;
7. anchor-only or M8 anchor-residual control marked as candidate promotion;
8. pseudo-modality `[fused,fused,fused]` used in a formal BR2 candidate;
9. invalid modality interaction slot active when a modality is missing;
10. pattern-SIP report missing or uniform coverage substituted for integrativeness;
11. deterministic axis prototypes are the only formal prototype source;
12. no-T2 myocardium used as edema negative;
13. no-T2 formal candidate emits edema voxels;
14. scar/edema refiners use identical ROI/crop/modality/loss behavior in a formal candidate;
15. scar refiner does not report small-ROI precision/HD95/remote-FP evidence;
16. edema refiner does not report large-ROI T2-present recall/HD95/no-T2 safety evidence;
17. refiner has no final-label effect but is claimed implemented;
18. hard subgroup metrics missing CenterB/CenterC/T2-present/edema-positive/no-T2 safety rows when present in evidence;
19. Cine is omitted as optional while M9 is marked ready;
20. Cine completion is only weight download/provenance;
21. Cine completion is frame0-only or descriptor-only;
22. Cine completion is single SyN/Demons smoke without final output labels;
23. untrained/unverified VoxelMorph is claimed ready;
24. Cine temporal dictionary exists but no final output labels or local metrics exist;
25. monitor/pending Slurm packet marked ready;
26. smoke-only or synthetic-only evidence marked formal training;
27. validation package/upload/hosted metric claim present;
28. M10 or fold expansion started automatically;
29. reviewer output written by executor.

Self-test must include one good fixture and all known-bad mutations. If any known-bad mutation passes, completion must be `M9_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

### 10. Allowed executor completion states

```text
M9_READY_FOR_REVIEW
M9_NEEDS_EVIDENCE
M9_NEEDS_REVISION
M9_SCIENTIFIC_UNDERTRAINED
M9_NEEDS_MONITOR
M9_RESOURCE_BLOCKED
M9_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE
```

`M9_READY_FOR_REVIEW` requires all required outputs, completed post-job aggregation, validator pass with `error_count=0`, known-bad self-tests fail closed, M8-like MyoPS training evidence, Cine final-output evidence or a controlled non-ready blocker, and no forbidden claims. It is not an audited decision.

### 11. Git and artifact policy

Commit only first-party code/helpers/tests and lightweight Markdown/CSV/JSON result files. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees.

Recommended local commit command after successful completion:

```bash
git add -f \
  src/care_myocardium/models/srr_blocks.py \
  src/care_myocardium/models/srr_propref.py \
  src/care_myocardium/models/proposal_prototypes.py \
  src/care_myocardium/models/srr_dictionary_memory.py \
  src/care_myocardium/losses/srr_losses.py \
  src/care_myocardium/cine/*.py \
  scripts/training/run_srr_propref_myops_fold0.py \
  scripts/training/run_cine_temporal_output_m9.py \
  scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py \
  scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py \
  jobs/src/run_srr_v3_m9_dictionary_fidelity_training_htzhulab.sh \
  jobs/src/run_srr_v3_m9_dictionary_fidelity_training.sh \
  jobs/src/run_srr_v3_m9_cine_temporal_output_htzhulab.sh \
  jobs/src/run_srr_v3_m9_cine_temporal_output.sh \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.md \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.csv \
  results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/*.json
git commit -m "Add M9 SRR dictionary fidelity and Cine output packet"
```

Do not push automatically unless the user explicitly instructs it in the Codex session.

# M9 follow-up executor: evidence reconciliation + validator re-audit

This shared M9 follow-up prompt was merged from the deleted M9 follow-up staging file. This is not M10, not route promotion, not fold expansion, not validation packaging/upload, not hosted metric claim, not leaderboard claim, and not scientific stop.

You are the Codex executor/controller for exactly one bounded M9 follow-up milestone: reconcile M9 evidence state, harden the validator, rerun aggregation/validation, and prepare the packet for a separate read-only re-audit.

Required protocol sentence: This is an executor/controller session for one M9 follow-up only. Stop after writing `completion_check.md` and `review_request.md`, force-add/commit the lightweight required result files and validator/code changes, then stop. Do not push automatically. Do not write `review.md` and do not start M10. The packet must be reviewed by a separate read-only reviewer before any continuation.

Background:

- Previous M9 result path: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/result.md`
- Previous M9 executor state: `M9_READY_FOR_REVIEW`
- Previous M9 executor route decision: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`
- Previous M9 review path: `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md`
- Previous M9 review decision: `M9_AUDITED_NEEDS_REVISION`
- Review blocker class: `evidence_state_and_validator_consistency`
- Next stage: `M9_FOLLOWUP_REAUDIT_BEFORE_ANY_M10`

M9 executor directionally supports no-promotion: the formal SRR-main candidates remain negative against the tracked M8 nnU-Net anchor, and Cine remains local proxy final-output evidence only. However, the independent reviewer found that the packet is not auditable because required tracked evidence files still contain pending/runtime-needed states while `completion_check.md` claims `M9_READY_FOR_REVIEW`. Therefore this bounded M9 follow-up repair and re-audit is required before any M10 planning.

## M9 follow-up required reading

Read these files before editing code or evidence:

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
README.md
prompts/CHATGPT_RULES.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/MILESTONE_REVIEW_PROTOCOL.md
prompts/THREAD_BOOTSTRAP_ROUTE_IMAGE_PROTOCOL.md
prompts/shared/EXECUTOR_PROMPTS.md
prompts/shared/REVIEWER_PROMPTS.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/result.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/completion_check.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_route_promotion_decision.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_next_required_action.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_dictionary_fidelity_matrix.csv
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_code_patch_summary.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_rrl_brr2_adaptation_contract.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_nnunet_role_audit.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_pathology_specific_refiner_contract.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_prototype_memory_summary.json
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_strict_validator_report.md
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_validator_selftest_report.md
scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py
scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py
```

If `review.md` is missing or its decision is not `M9_AUDITED_NEEDS_REVISION`, write a blocked follow-up packet and stop. Do not infer from chat summaries.

## M9 follow-up task identity and result policy

Continue using the M9 result directory:

```text
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/
```

This follow-up repairs the existing M9 packet. Do not create a new route result directory unless the validator architecture requires temporary fixtures. Do not launch new long training. Do not submit new Slurm jobs unless a required runtime artifact is genuinely missing and the packet cannot be reconciled from terminal M9 runtime outputs. If any new Slurm job is unavoidable, it must be justified in `m9_followup_commands_run.md` and the packet must remain non-ready until terminal accounting and aggregation are complete.

Separate three questions: evidence consistency, scientific direction, and next planning state. A validator repair does not make the route good. Negative metrics do not excuse stale pending evidence. A no-promotion executor direction is not an audited route-stop decision.

## M9 follow-up required repairs

### Reconcile stale pending evidence

Replace or correct stale pending/runtime-needed statuses in the required tracked evidence files. At minimum inspect and reconcile:

```text
m9_dictionary_fidelity_matrix.csv
m9_code_patch_summary.md
m9_rrl_brr2_adaptation_contract.md
m9_nnunet_role_audit.md
m9_pathology_specific_refiner_contract.md
m9_prototype_memory_summary.json
m9_route_promotion_decision.md
m9_next_required_action.md
completion_check.md
result.md
```

If runtime evidence exists, update statuses from `PENDING_RUNTIME`, `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`, `PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING`, `FORMAL_TRAINING_RUNNING`, or equivalent stale tokens to runtime-derived states with exact evidence paths. If runtime evidence does not exist, do not mark ready. Set completion to `M9_FOLLOWUP_NEEDS_EVIDENCE` and explain the missing evidence.

Required matrix rows must be evidence-backed: `true_br2_runtime_slot_usage`, `invalid_slot_mask_runtime`, `final_metric_causal_effect`, `prototype_memory_runtime_status`, `pathology_specific_refiner_runtime_status`, and `cine_final_output_runtime_status`. Each row must have a non-pending status and a concrete tracked evidence path. Do not invent evidence.

### Harden validator across Markdown, CSV, and JSON

Update `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py` so a ready packet fails closed when unresolved tokens appear anywhere in required Markdown, CSV, or JSON files, not just top-level Markdown.

The unresolved-token scan must include at least: `PENDING_RUNTIME`, `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`, `PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING`, `FORMAL_TRAINING_RUNNING`, `NEEDS_RUNTIME_EVIDENCE`, `RUNTIME_EVIDENCE_PENDING`, `SLURM JOBS PENDING`, `JOBS PENDING`, `AWAITING_SACCT`, `NEEDS_MONITOR`, `PENDING_MONITOR`, `JOB_SUBMITTED`, `PENDING_PRIORITY`, `RUNNING`, and `not sufficient for M9_READY_FOR_REVIEW`.

A ready packet may contain historical narrative about these tokens only if the row is explicitly marked `HISTORICAL_NONREADY_STATE_RESOLVED` and the same file contains the final resolved runtime status and evidence path. Simpler is better: remove stale non-ready language from final packet files.

### Add known-bad self-tests for this exact failure

Known-bad fixtures must fail closed:

```text
stale_pending_runtime_in_dictionary_fidelity_matrix
stale_partial_code_repair_in_code_patch_summary
stale_partial_brr2_contract_pending_runtime
stale_nnunet_controls_need_post_job_rows
stale_pathology_refiner_pending_runtime
stale_formal_training_running_in_prototype_memory_json
ready_packet_with_csv_pending_runtime_token
ready_packet_with_json_running_token
```

The self-test report must show one good fixture passes and all known-bad fixtures fail. If any known-bad mutation passes, completion must be `M9_FOLLOWUP_NEEDS_REVISION_VALIDATOR_NOT_FAIL_CLOSED`.

### Re-run aggregation only when needed

If tracked evidence can be refreshed from existing terminal runtime roots, rerun the M9 aggregator. Record the exact command, exit status, runtime roots, and changed files. Do not alter metrics by hand except to repair stale status text that clearly contradicts existing runtime-derived evidence. If metric tables are regenerated, cite the runtime source paths.

### Produce follow-up evidence

Add these lightweight files to the existing result directory:

```text
m9_followup_reconciliation_report.md
m9_followup_stale_status_scan.csv
m9_followup_validator_repair_summary.md
m9_followup_reaudit_request.md
m9_followup_commands_run.md
```

`m9_followup_reconciliation_report.md` must state one of `M9_FOLLOWUP_READY_FOR_REAUDIT`, `M9_FOLLOWUP_NEEDS_EVIDENCE`, `M9_FOLLOWUP_NEEDS_REVISION`, or `M9_FOLLOWUP_NEEDS_MONITOR`.

`m9_followup_stale_status_scan.csv` must include `file_path, scanned_type, unresolved_token_count, unresolved_tokens, final_status, action_taken`.

`m9_followup_validator_repair_summary.md` must explain the validator bug and the new fail-closed behavior. `m9_followup_reaudit_request.md` must request independent re-audit and explicitly state that the executor did not write `review.md` or start M10.

### Scientific interpretation after reconciliation

After the packet is internally consistent, write a short but explicit scientific interpretation in `m9_route_promotion_decision.md` and `m9_next_required_action.md`.

Allowed route decisions: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`, `M9_NEEDS_EVIDENCE`, `M9_NEEDS_REVISION`, `M9_SCIENTIFIC_UNDERTRAINED`, `M9_NEEDS_MONITOR`.

Do not write route promotion. Based on the current M9 metrics, the likely decision remains `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`, but this must be supported by reconciled evidence.

Allowed next actions: `GPT_REPLAN_AFTER_M9_NO_PROMOTION`, `NEEDS_EVIDENCE_BEFORE_NEXT_TASK`, `NEEDS_REVISION_BEFORE_REVIEW`, `NEEDS_MONITOR`, `GPT_PLAN_M10_AFTER_AUDITED_REVIEW_ONLY`.

Do not select `GPT_PLAN_M10_AFTER_AUDITED_REVIEW_ONLY` unless the separate reviewer later audits the corrected packet. The executor should normally stop at `GPT_REPLAN_AFTER_M9_NO_PROMOTION` or a non-ready state.

## M9 follow-up completion states

Allowed executor completion states:

```text
M9_FOLLOWUP_READY_FOR_REAUDIT
M9_FOLLOWUP_NEEDS_EVIDENCE
M9_FOLLOWUP_NEEDS_REVISION
M9_FOLLOWUP_NEEDS_MONITOR
M9_FOLLOWUP_RESOURCE_BLOCKED
M9_FOLLOWUP_BLOCKED_PREREQUISITE_REVIEW_MISSING
```

`M9_FOLLOWUP_READY_FOR_REAUDIT` requires reviewer blocker files reconciled or packet marked non-ready; validator scans required Markdown/CSV/JSON for stale unresolved states; validator real-packet pass with `error_count=0`; self-tests include the exact stale-pending known-bad fixtures and all fail closed; `completion_check.md` no longer conflicts with tracked evidence; no validation packaging/upload/hosted claim/fold expansion/M10.

Commit only first-party validator/aggregator changes and lightweight Markdown/CSV/JSON result files. Do not commit checkpoints, predictions, NIfTI files, upload zips, raw data, large logs, secrets, or full runtime trees. Do not push automatically.

## M10 executor/controller: SRR-v3 complete mechanism repair

# M10 — SRR-v3 complete mechanism repair, design attribution, and registration-gated Cine

This is the reconciled planner/critic staging contract. Its planner baseline is
`828735482396d6d727d2294e88c89868e3118ad3` on `agent/m10-planner-draft`.
The previous critic review against `e26895b99dc142ff64ea6e6f291600c6b67af98c` is superseded.
This file authorizes planning integration only after a matching critic review; it does not execute M10.

## Execution Contract

```yaml
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
```

The three executors are serial waves, not parallel workers. Wave 1 owns shared architecture and fidelity;
wave 2 owns formal MyoPS jobs/evidence after wave 1 is merged and frozen; wave 3 owns CineMA adaptation,
learned registration, and learned temporal aggregation after MyoPS terminal aggregation. The controller owns
continuity and all merges. This resolves the prior one-versus-three executor conflict in favor of three isolated,
sequential responsibilities while retaining `max_parallel: 1`.

## Grounding, lineage, and prerequisites

Required reviewed predecessor:

```text
wiki/current_state.yaml
results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md:
M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY
results/20260711_agent_flow_generic_protocol_repair/review.md:
AGENT_FLOW_GENERIC_PROTOCOL_REPAIR_AUDITED_GO
```

Required planning lineage:

```text
planner_branch: agent/m10-planner-draft
planner_draft_commit: 828735482396d6d727d2294e88c89868e3118ad3
critic_branch: agent/m10-planning-critic-repair
common_default_baseline: 925a00169649a523947e475204e68228cb8816f6
```

Controller bootstrap must verify that the planner draft commit is an ancestor of current HEAD and that the
planning-review token and canonical post-merge contract hash match the merged shared prompt sections. After
planning integration, the standalone staging file `prompts/shared/M10_srr_v3_complete_mechanism_repair.md` is
expected to be deleted and must not be required at runtime. Validate the merged prompt contract with:

```bash
python scripts/validation/hash_canonical_prompt_contract.py \
  --executor-file prompts/shared/EXECUTOR_PROMPTS.md \
  --executor-heading 'M10 executor/controller: SRR-v3 complete mechanism repair' \
  --reviewer-file prompts/shared/REVIEWER_PROMPTS.md \
  --reviewer-heading 'M10 reviewer: SRR-v3 complete mechanism repair'
```

The output must match `canonical_contract_sha256` in
`prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md`. The planning review's
`reviewed_contract_sha256` remains the historical pre-merge staging hash and is not recomputed from the deleted
staging path. Any token, lineage, or canonical hash mismatch yields `M10_BLOCKED_PREREQUISITE`.

The planner, critic, controller, mapper, finalizer, validator, and reviewer must read the active protocols and schemas,
root `wiki/README.md`, `wiki/MODEL.md`, `wiki/COMPONENTS.csv`, `wiki/architecture.yaml`,
`wiki/current_state.yaml`, `wiki/history/README.md`, `wiki/history/COMPARISON.md`, and every predecessor
component file matching `wiki/history/M09/components/*.md`. M08/M09 history remains immutable.

Diagram bootstrap is fixed:

```yaml
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CHATGPT_PROJECT_MATERIALS_AND_CURRENT_CONVERSATION
recovered_route_objective: availability-aware selective spatial retrieval, semantic shared/private/interaction dictionary, anatomy-guided pathology proposal, pathology-specific soft-ROI refinement, safe negative-space learning, and a registration-gated learned Cine temporal path
```

`nnU-Net` may be a same-split baseline, detached context/teacher, uncertainty source, or explicit safety comparator.
It is never the formal final-logit base and cannot silently replace SRR output.

## Fixed MyoPS tensor and architecture contract

Canonical modality order is `[LGE, T2, C0]`.

```text
x_m: B×1×H×W×D
a: B×3 binary availability
encoder channels: [32,64,128,256]
F_m^l: B×C_l×H_l×W_l×D_l
```

Missing modalities do not enter a stem as semantic zero images. Storage placeholders are permitted only when every
biased/normalized block is followed by the deterministic availability mask. Formal candidates use four scales;
`tiny_3scale` is smoke-only. D0-D3 parameter counts must be within ±5%, and FLOPs/patch, peak memory, and
trainable counts must be published.

### Exact 16-slot dictionary per scale

Each scale contains exactly:

```text
4 shared slots
2 LGE-private slots
2 T2-private slots
2 C0-private slots
2 LGE×T2 interaction slots
2 LGE×C0 interaction slots
2 T2×C0 interaction slots
```

Available features are projected to common channels. Shared input is projected from masked mean and variance;
private input is its modality feature; interaction input is
`Conv1x1([F_a,F_b,|F_a-F_b|,F_a⊙F_b])`. Every expert is an independent residual block:

```text
GN → SiLU → depthwise 3×3×3 Conv → pointwise 1×1×1 Conv
→ GN → SiLU → depthwise 3×3×3 Conv → pointwise 1×1×1 Conv + residual
```

Validity is deterministic:

```text
v_shared = 1[sum(a)>0]
v_private(m)=a_m
v_interaction(m,n)=a_m a_n
```

Invalid forward value, gate weight, gradient, and memory update must be zero. The strict threshold is
`max_invalid_weight <= 1e-8`; the evidence table also reports mean and per-case maxima.

### Four matched formal designs

All designs share encoder, anatomy, proposal/refiner capacity, split, augmentation, seed schedule, decode, and full-case
evaluation. They are true retrains, not inference toggles.

```text
D0_STATIC_MATCHED_PROPREF
  Sixteen parameter-matched residual experts with validity-masked fixed pathology mixtures.
  No content router, Pattern-SIP, prototype memory, or similarity term. Proposal/refiner remain.

D1_SPATIAL_BR2_PROPREF
  One-pass spatial content router over the 16-slot bank. No Pattern-SIP or prototype memory.

D2_HIERARCHICAL_BR2_PSIP_PROPREF
  Two-pass coarse-to-fine spatial router, proposal feedback, and real Pattern-SIP. No prototype memory.

D3_HIERARCHICAL_BR2_MEMORY_PROPREF
  D2 plus cross-fitted EMA+learnable-residual memory, safe hard negatives, pathology-specific proposal/refiner,
  and pair-valid feature-alignment hooks. This is the full candidate.
```

D0 is the parameter-matched no-retrieval control retained from the prior critic; D1-D3 preserve the latest Planner's
scientific design ladder.

### Two-pass lesion-conditioned spatial retrieval

Let `B_l` be the availability-masked base fusion and `E_lk` the 16 expert outputs. Anatomy retrieval uses feature and
availability evidence only and emits `Q_struct`, `P_union`, `P_LV`, and `P_RV`. Initial pathology evidence and
prototype maps are computed from `B_0`, avoiding circular dependence.

For pathology `t∈{scar,edema}`:

```text
q_tl^(0)(x) = phi_tl^(0)([B_l,e(a),P_union,P_LV,P_RV,d_remote,E_t^(0),S_t^+,S_t^-,U_t])
alpha_tl^(0) = entmax_1.5((A_tl^(0)+log(v_l+1e-12))/tau_l, dim=slot)
R_tl^(0) = sum_k alpha_tlk^(0) E_lk
p_t^(0) = sigmoid(H_t^(0)(R_t^(0)))

q_tl^(1)(x) = phi_tl^(1)([B_l,R_tl^(0),e(a),p_t^(0),P_union,P_LV,P_RV,d_remote,S_t^+,S_t^-,U_t])
alpha_tl^(1) = entmax_1.5((A_tl^(1)+log(v_l+1e-12))/tau_l, dim=slot)
R_tl = sum_k alpha_tlk^(1) E_lk
```

`e(a)` is 16-dimensional. Center ID is forbidden as a router input; center and train-only style clusters are audit groups.
Temperature is `1.5→0.7` by step 30000. The first 20% uses masked soft routing, 20%-70% uses top-4 straight-through,
and the final 30% uses top-2 straight-through. Inference uses valid top-2 and renormalization. No stop-gradient is allowed
from retrieved representation to final pathology output.

### Pattern-SIP and load control

For availability-pattern × train-style × hard-subgroup group `g` and ROI weight `r_i(x)`:

```text
u_tlkg = sum_{i in g,x} r_i(x) alpha_tlk(i,x) / (sum_{i in g,x} r_i(x)+eps)
gamma_tlk = (sum_{g in G_k} u_tlkg)^2 / (sum_{g in G_k} u_tlkg^2+eps)
L_PSIP = mean_shared relu(gamma_min-gamma)^2
         + mean_{t,l,g} KL(u_bar_tlg || pi_tlg)
         + 0.01 mean_x H(alpha_tl(x))
         + L_collapse
```

`G_k` contains only groups where slot `k` is legal. `pi` allocates 0.50 mass to shared slots, 0.35 to the pathology-key
private family (LGE for scar, T2 for edema), and 0.15 to valid interactions/auxiliary private slots. Pattern-SIP has an
independent implementation, log key, weight, computation graph, and gradient test; aliasing `dict_loss` is a blocker.

### Cross-fitted prototype memory and negative space

Each pathology has exactly 8 positive and 12 negative slots. Positive slots are split evenly between lesion core and boundary.
Negative slots are category-stratified across normal myocardium, blood/outside anatomy, acquisition/texture artifact, and
current-model hard false positives. Edema categories use only T2-present, edema-labeled cases.

Training cases are assigned to four deterministic memory shards by case hash. A case's proposal may use only prototypes
fitted from the other three shards. For each slot:

```text
mu <- L2Norm(0.99 mu + 0.01 mean(stopgrad(f)))
p = L2Norm(mu + 0.1 tanh(delta))
S_t^+(x)=0.07 logsumexp_j(cos(f_t(x),p_tj^+)/0.07)
S_t^-(x)=0.07 logsumexp_j(cos(f_t(x),p_tj^-)/0.07)
```

The FIFO capacity is 65536 embeddings per pathology. Ledgers contain source case, shard, count, age, assignment, category,
checkpoint, and safety reason. No-T2 myocardium is neither edema positive nor edema negative and has accepted count,
gradient, and update exactly zero.

Hard-negative replay uses current D3 out-of-fold full-case predictions, caps replay at 25% of sampled voxels and four components
per case, and records component provenance. It is followed by a bounded formal refresh and before/after evaluation.

Margin objectives are fixed:

```text
L_pos(t)=mean_{positive} relu(0.20-S_t^+ + S_t^-)
L_neg(t)=mean_{safe_negative} relu(0.20+S_t^+ - S_t^-)
```

### Anatomy, proposal, uncertainty, soft ROI, and final output

The anatomy head predicts `[background,myocardium,LV,RV]` plus `P_union`; scar and edema labels fold into myocardium for
anatomy supervision. The soft anatomy support is:

```text
G_ana = clamp(P_union + 0.25 MaxPool3D(P_union,k=9),0,1) (1-Q_LV)(1-Q_RV)
d_remote = clamp(EDT(1[stopgrad(G_ana)>0.30])/20mm,0,1)
```

Initial learned evidence `E_t` and prototype disagreement define:

```text
P_evidence,t=sigmoid(E_t)
P_proto,t=sigmoid(S_t^+-S_t^-)
U_t=0.5 H_binary(P_evidence,t)/log(2)+0.5|P_evidence,t-P_proto,t|
```

Final proposal logits are fixed; detached teacher/context cannot be tuned above the stated coefficients:

```text
z_prop,t = E_t + S_t^+ - lambda_neg,t S_t^-
           + lambda_ana,t logit(clamp(G_ana,1e-4,1-1e-4))
           - lambda_remote,t d_remote - lambda_unc,t U_t
           + lambda_teacher,t C_t_detached
```

| pathology | lambda_neg | lambda_ana | lambda_remote | lambda_unc | lambda_teacher |
|---|---:|---:|---:|---:|---:|
| scar | 1.25 | 0.75 | 0.60 | 0.35 | 0.10 |
| edema | 1.00 | 0.60 | 0.40 | 0.25 | 0.05 |

Soft ROI and refinement are:

```text
G_prop,t=sigmoid(z_prop,t)
rho_t=clamp(G_ana(0.20+0.80 G_prop,t)(1-U_t)+0.05 MaxPool3D(G_prop,t,k=9),0,1)
Delta z_t = delta_t tanh(H_t([R_t^0,E_t,S_t^+,S_t^-,G_ana,d_remote,U_t,G_prop,t]))
z_final,t = z_prop,t + rho_t Delta z_t
```

Scar refiner has three residual blocks, dilation `[1,1,2]`, 64 channels, `delta_scar=2.0`. Edema refiner has four residual
blocks, dilation `[1,2,3,1]`, 64 channels, `delta_edema=1.5`. Crop boxes are compute boundaries only; the gate is soft.
An empty proposal may use anatomy-union ROI and must record `ANATOMY_FALLBACK`; image-center seed is forbidden.

The formal six-class probability relation is:

```text
P_scar=sigmoid(z_final,scar)
P_edema=a_T2 q_edema (1-P_scar) sigmoid(z_final,edema)
r=1-P_scar-P_edema
[P_bg,P_myo,P_LV,P_RV]=r Q_struct
P_final=[P_bg,P_myo,P_LV,P_RV,P_edema,P_scar]
yhat=argmax(P_final)
```

`q_edema=1[T2 present and edema label semantics available]`. No-T2 export has `P_edema=0` exactly. The formal output
records `final_output_base: SRR_PROPOSAL_REFINEMENT`; no anchor identity, silent fallback, or label replacement is allowed.

### Pair-valid MyoPS feature alignment

D3 implements LGE-reference feature alignment for LGE-T2 and LGE-C0 at the two coarsest decoder scales. It predicts a
stationary velocity, uses five scaling-and-squaring steps, and optimizes local NCC/feature similarity, anatomy consistency,
smoothness, and Jacobian folding penalty. It only runs when both modalities exist and feeds interaction experts. Formal evidence
includes aligned and unaligned controls, pair masks, overlap, Jacobian/folding, displacement, and final-output effect. It is a
required trained control but may remain disabled in the selected checkpoint when it fails the predeclared help/harm gate.

## Loss and optimization contract

```text
L_total = w_ana L_anatomy + w_full L_final6
        + w_prop,s L_prop,scar + q_edema w_prop,e L_prop,edema
        + w_ref,s L_ref,scar + q_edema w_ref,e L_ref,edema
        + w_pos L_pos + w_neg L_neg + w_mem L_memory
        + w_PSIP L_PSIP + w_invalid L_invalid
        + w_roi L_ROI + w_boundary L_boundary + w_HD L_HD
        + w_align L_align + w_teacher L_detached_teacher + w_relation L_scar_to_edema
```

Anatomy uses DiceCE. Final and proposal terms use DiceCE; scar adds precision-aware Focal-Tversky and boundary/HD terms;
edema adds recall-aware Focal-Tversky and every edema term is `q_edema` masked. The soft scar-to-edema relation is enabled
only for T2-present, low-uncertainty edema and never imposes hard containment.

Every component is classified as `real_optimized_loss`, `diagnostic_metric_only`, or `disabled_with_reason`. Alias and
placeholder-zero losses are forbidden. Changing any active weight from 0 to 10 must change total loss and intended parameter
gradient. Each event records raw/weighted value, configured/actual weight, EMA, gradient norm, parameter group, masked
denominator, and dominance fraction.

Fixed optimizer:

```text
AdamW; betas=(0.9,0.999); weight_decay=1e-4
MyoPS base lr=3e-4; refresh/alignment lr=1e-4
Cine adapter/temporal lr=2e-4; registration lr=1e-4
5% linear warmup; cosine floor=1e-2 of peak; AMP; grad clip=5.0
patch batch=2; gradient accumulation=2
```

Four MyoPS phases are A anatomy/evidence warmup, B dictionary/proposal/PSIP/memory, C refiner/full-output/boundary-HD,
and D current-model hard-negative refresh plus low-LR calibration. Modality dropout applies only to originally complete cases:
C0 0.20, T2 0.20, never LGE; T2 dropout sets `q_edema=0` rather than creating a negative.

## Minimum effective training and checkpoint selection

```yaml
minimum_effective_training:
  min_optimizer_steps: 220000
  min_train_loop_seconds: 72000
  min_eval_cases: 44
  min_validation_events: 120
  require_one_batch_overfit: true
  require_prediction_sanity: true
  require_loss_decrease: true
  require_loss_stability: true
  require_same_split_baseline: true
  require_cache_isolation: true
  require_challenge_metric_checkpoint_selection: true
  require_hard_subgroup_metrics: true
  require_terminal_slurm_accounting: true
  require_post_job_aggregation: true
```

| formal run | min steps | min train-loop seconds | validation events | full-case events | eval cases |
|---|---:|---:|---:|---:|---:|
| D0 static matched | 20000 | 7200 | 12 | 4 | 44 |
| D1 spatial BR2 | 25000 | 9000 | 15 | 5 | 44 |
| D2 hierarchical BR2+PSIP | 25000 | 9000 | 15 | 5 | 44 |
| D3 full memory PropRef | 45000 | 14400 | 22 | 8 | 44 |
| D3 hard-negative refresh | 20000 | 5400 | 10 | 4 | 44 |
| D3 no-nnU-Net-context retrain | 20000 | 5400 | 10 | 4 | 44 |
| MyoPS alignment train/control | 10000 | 3600 | 8 | 3 | 44 |
| CineMA CARE adapter | 10000 | 3600 | 8 | 3 | at least 12 |
| learned Cine registration | 25000 | 7200 | 10 | 4 | at least 12 |
| learned Cine temporal dictionary | 20000 | 7200 | 10 | 4 | at least 12 |

The sum is 220000 steps and 72000 effective train-loop seconds. Every row is blocking. Queue time, sleep, cache generation,
repeated smoke, failed startup, and reset-counter restart do not count. Each job walltime request is <=8 hours. Early stopping is
forbidden before that row's complete steps, seconds, and event minima; any earlier termination is `SCIENTIFIC_UNDERTRAINED`.
Preemption/OOM resumes only from a scheduled checkpoint with matching code/config/split/cache hashes and cumulative counters.

One-batch overfit must reduce loss >=90%, produce nonempty target prediction, and show positive gradient for encoder, router,
experts, memory residual, proposal, and refiner. Formal stability requires first-to-last 10-event median loss decrease >=20%,
last-five-event coefficient of variation <=0.15 or a documented stable plateau, no prediction-volume explosion, and no active
component dominating >70% or falling below 0.5% for three windows without a valid mask reason.

Save every 2500 steps. Every scheduled checkpoint runs 44-case full-case evaluation, including at least 16 T2-present
edema-positive cases, 7 CenterB cases, and 9 CenterC cases. Patch loss never selects the checkpoint. Eligibility requires finite
metrics, valid labels, no-T2 edema max <=1e-6, positive-case nonempty prediction on >=80%, volume ratio `[0.05,20]` on >=95%,
and exact split/cache/decode hashes.

For pathology `t`:

```text
g_t = Dice_t-Dice_anchor,t
      -0.01 clip((HD95_t-HD95_anchor,t)/10mm,-5,5)
      -0.02 clip((remoteFP_t-remoteFP_anchor,t)/(remoteFP_anchor,t+1),-2,2)
S_checkpoint=min(g_scar,g_edema)+0.25(g_scar+g_edema)
```

Select maximum eligible score, tie-breaking by lower worst-case HD95 then earlier step. Publish every scheduled checkpoint.
Threshold and component calibration use train/inner-validation only and are frozen before the 44-case evaluation.

Hard subgroups include scar-positive, T2-present edema-positive, modality patterns, every center, small/large lesion quartiles,
worst-anchor-HD95 quintile, anchor remote-FP cases, and empty-GT cases reported separately. Scar and edema gates remain
pathology-specific; foreground mean cannot hide harm.

## Controls and causal classification

Same-split nnU-Net predictions require matching case IDs, split, preprocessing, label map, decode, and metric hashes. D0-D3,
no-context retrain, pre/post refresh, and alignment train/control are the only matched L4 comparisons. The selected D3 checkpoint
also runs same-case interventions:

```text
static_mixture
dictionary_uniform_valid
top_pathology_slots_zeroed
spatial_router_to_global
PSIP_stateless
prototype_memory_off
anatomy_prior_flat
proposal_only
scar_refiner_off
edema_refiner_off
both_refiners_off
uncertainty_flat
nnunet_context_off
alignment_off
swapped_positive_negative_known_bad
```

For each component/pathology publish call count, gradient norm, activation variance, proposal/refiner/final-logit delta, changed
voxels/components, Dice, HD95, and remote-FP delta. Classification is exactly one of:

```text
NOT_CALLED
CALLED_NO_GRADIENT
GRADIENT_NO_OUTPUT_EFFECT
OUTPUT_EFFECT_NO_BENEFIT
OUTPUT_EFFECT_WITH_BENEFIT
UNDERTRAINED
PIPELINE_BUG
MECHANISM_NO_SIGNAL_AFTER_ADEQUATE_MATCHED_TEST
```

The last state requires adequate formal training, a matched retrain, true output intervention, and a clean pipeline.

## Registration-gated Cine lane

Cine is a blocking secondary lane and cannot rescue or reinterpret MyoPS. Wave 3 first verifies the license, model identifier,
commit, SHA256, preprocessing, label map, orientation, spacing, and time axis of the approved CineMA asset. CineMA supplies
per-frame anatomy features/logits and uncertainty; the CARE adapter trains on CARE data, adapts the final two blocks or an
explicit LoRA/adapter, and is compared with a random-initialization capacity-matched adapter.

### Learned diffeomorphic registration

Input is `I: B×T×1×H×W×D`; ED is reference, ES is minimum predicted LV volume. Select
`max(8,ceil(4T/6))` frames, including ED, ES, uniformly spaced and motion-salient frames. A 3D U-Net with channels
`[16,32,64,128]` predicts symmetric stationary velocities. Seven scaling-and-squaring steps produce physical-space warps.

```text
L_reg = 1.0[1-LNCC_9^3(I0,W(It,phi_0<-t))]
      + 1.0 DiceLoss(Q0,W(Qt,phi_0<-t))
      + 0.05 ||grad v_t||^2
      + 0.10 mean(relu(-det J(phi))^2)
      + 0.10 ||phi_0<-t o phi_t<-0 - Id||_1
```

ANTs SyN is the paired classical control. Demons, optical flow, untrained checkpoints, frame0 copying, and descriptor-only
correspondence are forbidden formal substitutes. Formal held-out QC covers >=12 cases and >=60 non-reference pairs and requires:

```text
median warped-anatomy Dice gain >=0.03
>=90% cases non-worse in mean anatomy Dice
LNCC improves on >=75% pairs
negative-Jacobian fraction <=0.5% every case and <=0.1% median
99th-percentile displacement <=35mm and inside FOV
median inverse-consistency error <=2 voxels
learned registration non-inferior to SyN within 0.01 Dice, with no folding violation,
and either >=25% lower runtime or fewer failures
```

Every case/frame remains in the denominator with overlap, HD95, LNCC, displacement, folding, cycle error, and failure reason.
Persistent gate failure blocks learned temporal training; frame0 fallback cannot satisfy M10.

### Learned temporal dictionary

After registration passes, warp CineMA feature, anatomy, texture, velocity, Jacobian, and residual into ED space. Exactly eight
temporal slots represent ED anatomy anchor, early/late systolic contraction, early/late diastolic relaxation, motion magnitude,
registered texture residual, and registration-uncertainty safety. For frame `t`:

```text
Z_t=[W(F_t,phi),||v_t||,detJ(phi),|I0-W(It,phi)|,W(Q_t,phi),time_embed(t/T)]
beta_tk=entmax_1.5((Router_temp(Z_t)-M_qc)/0.7,dim=(t,k))
T_ED=sum_tk beta_tk E_k(Z_t)
Q_cine=softmax(H_cine([F0,T_ED,Q0]))
```

`M_qc=inf` for an invalid frame. Fewer than four valid non-reference frames is a registration failure, not frame0 completion.

```text
L_cine=DiceCE(Q_cine,Y_ED)
      +0.50 mean_t DiceLoss(Q_cine,W(Q_t,phi))
      +0.20 mean_t ||Q_cine-W(Q_t,phi)||_1 (1-U_reg,t)
      +0.05 L_temporal_load
```

Same-subset controls are frame0 matched backbone, unregistered mean, registered mean, deterministic union, M9 proxy, and
no-temporal-dictionary. Report myocardium Dice/HD95, temporal jitter, topology failure, final-label changed voxels, and per-case
help/harm. No hosted readiness claim is permitted.

## Exact task graph and evidence

All are blocking and exact paths are required:

```text
results/20260711_srr_v3_m10_architecture_fidelity/
results/20260711_srr_v3_m10_mechanism_smoke/
results/20260711_srr_v3_m10_myops_d0_control/
results/20260711_srr_v3_m10_myops_d1_spatial_br2/
results/20260711_srr_v3_m10_myops_d2_hierarchical_psip/
results/20260711_srr_v3_m10_myops_d3_full_propref/
results/20260711_srr_v3_m10_hard_negative_refresh/
results/20260711_srr_v3_m10_no_nnunet_context_control/
results/20260711_srr_v3_m10_alignment_control/
results/20260711_srr_v3_m10_component_causal_audit/
results/20260711_srr_v3_m10_cinema_adapter/
results/20260711_srr_v3_m10_cine_registration/
results/20260711_srr_v3_m10_cine_learned_temporal/
results/20260711_srr_v3_m10_completion_check/
results/20260711_srr_v3_m10_complete_mechanism_repair/
```

Every formal training directory contains `result.md`, `training_budget_ledger.csv`, `loss_stability.csv`,
`validation_events.csv`, `checkpoint_selection.csv`, `case_metrics.csv`, `hard_subgroup_metrics.csv`,
`prediction_sanity.md`, `runtime_manifest.json`, `commands_run.md`, and `MANIFEST.md`, plus mechanism-specific
router/memory/proposal/refiner/registration/Cine evidence. The controller packet contains every file required by
`prompts/schemas/controller_packet.schema.yaml`, all three executor completion receipts, mapper draft/final,
architecture deltas, finalizer state, validator report, completion check, review request, and reviewer prompt.

The strict validator scans Markdown/CSV/JSON and must reject missing frontmatter, stale planning hash, invalid plan lane,
undertraining, patch-loss selection, cache collision, nonzero invalid slots, zero router/expert gradients, SIP alias,
deterministic/no-OOF prototypes, unsafe edema negatives, no final-output effect, hidden anchor identity, fake causal tables,
monitor completion, missing aggregation, folding-heavy/single-case/untrained registration, frame0/union-only Cine, excluded
failure cases, and stale wiki/figures. Known-bad includes swapped prototypes, unsafe no-T2 negative, invalid private slot,
hidden anchor identity, folding-heavy registration, and frame0-only Cine.

## Slurm continuity and finalizers

`htzhulab` is default; fallbacks/routing races follow the repository Slurm skill with isolated roots, logs, and locks. Each
formal training chain must pass compute-environment preflight before the first GPU job. Training stages that require upstream
success use `afterok`; `afterany` is reserved for accounting/finalizer jobs over all attempts. Each wave submits an `afterany`
wave finalizer over all of its job IDs and cannot return a completion token until terminal accounting and post-job aggregation
succeed. The controller retains every old and replacement job ID across waves and submits the global durable finalizer over all
recorded attempts. Failed startup attempts keep zero training credit and may be retried only as same-executor, same-scope
replacement attempts with matching code/config/split fingerprints. `PENDING`, `RUNNING`, `CONFIGURING`, `COMPLETING`, and `AWAITING_SACCT` map to
`NEEDS_MONITOR`; scheduler saturation requires 12 checks at two-hour intervals over 24 hours.

`FINALIZER_A` records terminal state, exit code, elapsed, partition, log, runtime root, checkpoint provenance, output checks,
and aggregation command; it writes `finalizer_state.json` as `READY_FOR_MAPPER_FINAL` or a fail-closed state. After mapper
final, `FINALIZER_B` runs packet, handoff, wiki/history, generated-figure, known-bad, and `git diff --check` validation, then
creates exactly one local lightweight packet commit. No checkpoint, prediction, NIfTI, zip, raw data, large log, or secret is
committed. Controller pre-review fields remain `NOT_REVIEWED`/`AWAITING_REVIEW`, and push is skipped.

## Wiki and history

Mapper draft runs after wave 1 merge. Mapper final runs only after all formal runtime aggregation. It updates root wiki,
`COMPONENTS.csv`, `architecture.yaml`, model-current/model-gap/execution-flow figures, and appends an M09→M10 candidate
comparison. It creates `wiki/history/M10/` with all component files, architecture and figures marked
`candidate_unreviewed`, `review_token: NOT_REVIEWED`. It never rewrites M08/M09. `wiki/current_state.yaml` remains on
M09 until the independent runtime review is committed and a later reconciliation task advances it.

## Controller Prompt

Before executing the scientific task, enforce the hard-gate policy: exact task graph, agent-flow v2 execution contract, strict
validator, completion-check-before-final-audit, minimum effective training, current-bad-packet regression, mapper/wiki/fingerprint
gates, and SRR diagram-bootstrap evidence. If any gate fails, stop with NEEDS_REVISION or NEEDS_EVIDENCE.

Launch exactly the three serial executor waves in the validated plan. Merge only after each completion receipt. Freeze shared
architecture during wave 2; any wiring defect returns to wave 1 rather than being hot-patched. Submit Cine temporal only after
the registration gate passes. Maintain durable continuity and stop after the local final packet and review request. Do not write
`review.md`, push, package/upload validation, claim hosted metrics, promote, stop the route, or start M11.

This is an executor/controller session for one milestone only. Stop after writing completion_check.md and review_request.md,
force-add/commit the lightweight required result files, then stop. Do not push automatically. Do not write review.md and do not
start the next milestone.

## Executor Worker Contract

Wave 1 implements the fixed shared architecture, losses, tests, fidelity and smoke only. Wave 2 uses merged frozen architecture
to run D0→D1→D2→D3→refresh→no-context→alignment formal work and evidence. Wave 3 verifies CineMA provenance,
implements/trains the CARE adapter, learned diffeomorphic registration, registration gate, learned temporal dictionary, and
same-subset controls. Executors remain inside plan write scopes, use isolated worktrees/branches/results/runtime/logs/locks,
write completion receipts, and never merge themselves, self-review, push, or redesign formulas/budgets.

## Mapper Contract

The mapper uses `.agents/skills/care-mapper/SKILL.md`, reads first-party source/config/entrypoints and lightweight evidence,
and does not inspect raw data, checkpoints, NIfTI, large logs, secrets, or upload packages. It does not modify model code or write
`review.md`. Any source/evidence/wiki fingerprint mismatch is stale and blocks `FINALIZER_B`.

## M10 follow-up executor/controller: contract reconciliation, Wave 2 evidence completion, and Cine fidelity repair

## Execution Contract

The machine-readable contract above is authoritative. The exact mirror is:

```yaml
task_key: 20260714_srr_v3_m10_continuation_reconciliation
task_kind: scientific_milestone
task_type: controller
controller_mode: true
milestone_number: 10
milestone_id: M10
status: READY_FOR_CODEX_MERGE
risk_level: high
route_change: false
scientific_decision_scope: mechanism_signal
execution_mode: controller_supervised
requires_execution_controller: true
executor_slots: 1
executor_count: 3
parallel_execution_allowed: false
executor_plan_path: prompts/tasks/20260714_srr_v3_m10_continuation_reconciliation_executor_plan.yaml
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: slurm_dependency
review_mode: independent_thread
reviewer: separate_readonly
review_required: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
route_promotion_gate: independent_runtime_reviewer_and_later_gpt_user_decision_only
experiment_adequacy_gate: inherited_wave2_fingerprint_and_budget_validation_plus_new_cine_minimum_effective_training
route_negative_gate: adequate_matched_final_output_interventions_or_faithful_registration_negative_packet_only
scientific_completion_gate: independent_runtime_review_required
diagnostic_publication_gate: reviewed_lightweight_packet_only
diagnostic_publication_scope: md_csv_json_only
blocked_after_diagnostic_publication: validation_upload_route_promotion_scientific_stop_m11
planning_review_required: true
planning_reviewer: separate_gpt_thread
planning_review_path: prompts/tasks/20260714_srr_v3_m10_continuation_reconciliation_planning_review.md
planning_review_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
planning_reviewed_commit: 4cce847edc0658df611da26a4b9070025f1ba170
```

This is a bounded continuation of M10. It is not M11, not a route promotion, not a validation-package task, and not permission to rewrite historical M10 review evidence. The controller may create one local lightweight final packet commit and must stop before independent runtime review. No runtime role may push.

The route objective recovered from SRR-v2, SRR-v2.5, and SRR-v3 remains: availability-aware modality-specific handling; a real shared/private/interaction semantic retrieval bank and train/OOF prototype memory; anatomy-guided scar/edema proposal; pathology-specific soft-ROI refinement; safe no-T2 edema supervision; and a final output causally owned by SRR. nnU-Net is anchor/context/evidence/safety only. Cine remains registration-aware anatomy-first temporal retrieval.
## Controller Prompt

You are the Codex controller for exactly one M10 follow-up. Before any scientific work, enforce the current hard-gate policy, executor-plan validation, Planner/Critic lineage, stable staging hash, exact task graph, source/config/split fingerprints, minimum-effective-training rules, monitor-packet prohibition, mapper/wiki gates, and route-diagram bootstrap evidence. If a required gate fails, write a fail-closed lightweight packet and stop. Do not reinterpret a missing artifact as a negative result.

### 1. Contract-hash reconciliation

Treat the historical hashes as immutable provenance:

```text
old reviewed canonical hash: 5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64
current parent canonical hash: 955f6ab31e523123ba339e5b1732b78b304f099b9ce92bc896dfbb1e5d76653f
operational repair commit: c53fa06
```

`c53fa06` added compute preflight, bounded fingerprint-preserving retry, `afterok` training dependencies, `afterany` accounting/finalizer dependencies, old/replacement job retention, and zero-credit failed starts. These are legitimate execution-contract additions but were not bound by the old planning review. Do not edit the old review hash and do not roll back the repair. Codex planning integration must create a new canonical M10 follow-up section and bind it to this staging hash and planning review.

### 2. Three serial executors and freeze boundaries

Launch exactly the three executors declared in the plan, with `executor_slots: 1` and `max_parallel: 1`:

```text
Wave F1  m10_followup_wave2_reconciliation_executor
Wave F2  m10_followup_cine_fidelity_executor
Wave F3  m10_followup_cine_runtime_executor
```

F1 may read and evaluate inherited MyoPS runtime outputs but may not train or modify MyoPS/Cine implementation. F2 may modify only new Cine follow-up implementation, tests, configs, entrypoints, and jobs; it may not train formally or alter MyoPS. After F2 merge, the controller writes a freeze receipt containing exact source/config/test/entrypoint/job hashes. F3 must validate that receipt before preflight and may submit/monitor/aggregate only; it cannot modify implementation. Any required implementation change returns `NEEDS_REVISION_RETURN_TO_CINE_FIDELITY_WAVE` rather than being hot-patched in F3.

### 3. Wave F1: inherit training, not invalid decisions

The existing Wave 2 MyoPS formal runs are inherited only after a machine-readable fingerprint audit confirms exact agreement of code, config, split, case IDs, label map, preprocessing, decode, checkpoint inventory, runtime summary, terminal Slurm accounting, and declared minimum-effective-training fields. The expected inherited phases are D0, D1, D2, D3, hard-negative refresh, no-context control, and alignment control. If a fingerprint or required runtime artifact differs, mark only the affected phase `INHERITANCE_BLOCKED`; do not silently retrain. New training requires a later explicit planning decision.

The inherited optimizer-step, train-loop-second, validation-event, and 44-case budgets may receive credit only from terminal aggregated evidence. Failed startup, OOM, superseded, cancelled, monitor-only, or reset-counter attempts receive zero credit.

#### Challenge-facing all-checkpoint selection

`legacy_val_patch_loss`, training loss, patch loss, checkpoint filename, or prior `checkpoint_best` designation is forbidden as the formal selector. Enumerate every recoverable scheduled checkpoint, including scheduled validation saves, prior best, and final checkpoints. Reload each checkpoint and run the same 44-case challenge-facing evaluation with exact split/preprocessing/label/decode/metric hashes and the original eligibility gates.

For pathology `t`:

```text
g_t = Dice_t - Dice_anchor,t
      - 0.01 clip((HD95_t - HD95_anchor,t)/10mm, -5, 5)
      - 0.02 clip((remoteFP_t - remoteFP_anchor,t)/(remoteFP_anchor,t + 1), -2, 2)
S_checkpoint = min(g_scar, g_edema) + 0.25(g_scar + g_edema)
```

Select the maximum eligible score, then lower worst-case HD95, then earlier step. Eligibility requires finite metrics, exact case set and hashes, no-T2 edema maximum probability `<=1e-6`, nonempty positive-case prediction on at least 80%, and prediction-volume ratio `[0.05,20]` on at least 95%. Threshold/component calibration must be train/inner-validation only and frozen before the 44-case evaluation. Publish every evaluated checkpoint and a reason for every exclusion.

#### D2 and D3 true final-output interventions

At the separately selected D2 and D3 checkpoints, run same-case, same-checkpoint interventions without retraining:

```text
static_mixture
dictionary_uniform_valid
top_pathology_slots_zeroed
spatial_router_to_global
PSIP_stateless
prototype_memory_off
anatomy_prior_flat
proposal_only
scar_refiner_off
edema_refiner_off
both_refiners_off
uncertainty_flat
nnunet_context_off
alignment_off
swapped_positive_negative_known_bad
```

Every intervention must execute the real inference path and report per component and pathology: call count, gradient-bearing status from the inherited training evidence, activation variance, proposal-logit delta, refiner-logit delta, final-logit delta, changed voxels, changed components, Dice, HD95, remote-FP, and per-case help/harm. Placeholders such as `SEE_RUNTIME_TABLES`, claim-only CSVs, or diagnostic tensors disconnected from final output are blockers.

Classify each component exactly once as:

```text
NOT_CALLED
CALLED_NO_GRADIENT
GRADIENT_NO_OUTPUT_EFFECT
OUTPUT_EFFECT_NO_BENEFIT
OUTPUT_EFFECT_WITH_BENEFIT
UNDERTRAINED
PIPELINE_BUG
MECHANISM_NO_SIGNAL_AFTER_ADEQUATE_MATCHED_TEST
```

The final state requires adequate inherited training, a matched control where required, a clean pipeline, and a true final-output intervention. It cannot be inferred from a zero delta caused by a bug or a missing call.

### 4. Wave F2: repair Cine implementation fidelity before any new formal run

The old CineMA adapter and registration outputs are implementation-fidelity failures, not adequate scientific negative evidence. F2 must replace them with first-party follow-up paths while retaining historical packets unchanged.

#### CineMA provenance, adaptation, and control

The adapter must record the external asset source URL/repository, model identifier, source commit/tag, license, weight filename and SHA256, architecture identifier, preprocessing, label map, orientation, spacing, time-axis convention, and every CARE case/frame used. Unverifiable license or weight identity is a blocker.

CineMA must supply per-frame multiclass anatomy logits or probabilities, nontrivial intermediate features, and calibrated uncertainty. A binary foreground mask is not a valid substitute. Adapt the final two blocks, an explicit LoRA path, or an equivalently declared trainable adapter while retaining a verified pretrained path. Train a capacity-matched random-initialization control with identical architecture, trainable parameter count tolerance, cases, frame schedule, augmentation, optimizer, steps, seconds, validation events, and selection rule.

Evaluate all scheduled adapter/control checkpoints on the same held-out cases. Select each checkpoint by a predeclared anatomy-facing score using myocardium/LV/RV Dice, HD95, topology failure, temporal consistency, and uncertainty calibration; reload the selected checkpoint before final evidence export. The comparison must publish `adapted_minus_random_init` per case and class, and classify the pretrained contribution as `CINEMA_PRETRAINED_BENEFIT`, `CINEMA_RANDOM_INIT_NONINFERIOR`, or `CINEMA_COMPARISON_UNDERTRAINED`. Either adequately trained outcome may continue to registration, but only the selected source may feed registration/temporal execution and no CineMA benefit may be claimed when random initialization is noninferior.

Missing non-reference predictions must be a recorded frame failure. Falling back to frame0, binarizing the prior, or training an unrelated small CNN without verified CineMA features/logits is forbidden.

#### Learned diffeomorphic registration

Input is `B×T×1×H×W×D`; ED is the reference and ES is the minimum selected-checkpoint LV volume. Select `max(8,ceil(4T/6))` frames including ED, ES, uniformly spaced frames, and motion-salient frames. A 3D U-Net with channels `[16,32,64,128]` predicts both directions of a stationary velocity field. Convert normalized-grid and voxel/physical units explicitly. Seven scaling-and-squaring steps must produce `phi_0<-t` and `phi_t<-0`; direct velocity-as-displacement is forbidden.

Use the complete objective:

```text
L_reg = 1.00 [1 - LNCC_9x9x9(I0, W(It, phi_0<-t))]
      + 1.00 DiceLoss(Q0, W(Qt, phi_0<-t))
      + 0.05 ||grad v||^2
      + 0.10 mean(relu(-det J(phi))^2)
      + 0.10 ||phi_0<-t o phi_t<-0 - Id||_1
```

The anatomy term must use the selected adapter/control checkpoint and the registered multiclass probabilities. Compute true Jacobian determinants, physical displacement, inverse-consistency composition error, overlap, HD95, LNCC, and runtime. Proxy folding, displacement magnitude as inverse consistency, or pair-level quantities relabeled as case-level are forbidden.

Run a real paired ANTs SyN control with command, version, parameters, transform files, runtime, failures, and same-case/frame metrics. A synthetic `after=max(before,learned-constant)` proxy is forbidden.

Every scheduled registration checkpoint must be evaluated on at least 12 held-out cases and 60 non-reference pairs. Select by the predeclared registration score among checkpoints satisfying all safety conditions, reload that selected checkpoint, and only then apply the unchanged gate:

```text
median warped-anatomy Dice gain >= 0.03
>= 90% cases non-worse in mean anatomy Dice
LNCC improves on >= 75% pairs
negative-Jacobian fraction <= 0.5% for every case and <= 0.1% median
99th-percentile displacement <= 35 mm and inside the FOV
median inverse-consistency error <= 2 voxels
learned registration noninferior to SyN within 0.01 Dice with no folding violation
and either >= 25% lower runtime or fewer failures
```

Case non-worse is computed after aggregating all valid frames per case; the denominator contains every eligible case, including failures. Every case/frame row includes failure reason and remains in denominators according to the declared failure policy.

#### Temporal path

Only a passed, selected, reloaded registration checkpoint may launch temporal training. Warp selected-source CineMA features, multiclass anatomy, texture, velocity, Jacobian, residual, and registration uncertainty into ED space. Use exactly eight temporal slots: ED anatomy anchor, early/late systolic contraction, early/late diastolic relaxation, motion magnitude, registered texture residual, and registration-uncertainty safety. Fewer than four valid non-reference frames is a registration failure, not frame0 completion.

The temporal dictionary must change final logits/labels and be compared on the same subset with frame0 matched backbone, unregistered mean, registered mean, deterministic union, M9 proxy, and no-temporal-dictionary controls. Report myocardium Dice/HD95, temporal jitter, topology failure, changed voxels/components, and per-case help/harm.

### 5. Faithful registration-negative closure

If and only if the selected registration checkpoint satisfies all minimum-effective-training, provenance, checkpoint-reload, real-SyN, denominator, metric, and strict-validator requirements but still fails the unchanged gate, do not train the temporal dictionary. Create a terminal packet with:

```text
completion_state: READY_FOR_REVIEW_CINE_REGISTRATION_NEGATIVE
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
```

This is an operationally reviewable M10 negative-registration closure, not route stop or promotion. It must include the selected checkpoint, all failed gate fields, per-case/frame evidence, real SyN comparison, adequacy receipts, and zero temporal-training credit. The independent runtime reviewer decides whether the negative evidence is adequate. Implementation failure, undertraining, proxy metrics, missing SyN, or stale/fingerprint-mismatched evidence must instead return `NEEDS_REVISION` or `NEEDS_EVIDENCE`.

### 6. Durable continuity, outputs, and stop boundary

Training-to-training dependencies use `afterok`. Accounting/finalizer dependencies over all old and replacement attempts use `afterany`. Every formal chain requires compute-node preflight with Python/import/optimizer/CUDA/config/contract/writability/code-config-split fingerprints. Bounded same-scope retries preserve scientific semantics and retain all old/replacement job IDs; failed starts receive zero training credit.

The global finalizer must capture all Wave F1 evaluation jobs and Wave F3 formal jobs, run terminal accounting and post-job aggregation, then invoke mapper final, strict packet/handoff/wiki/history/figure validators, known-bad fixtures, and `git diff --check`. Required controller outputs include:

This is the durable finalizer contract: the controller/global finalizer must capture all old and replacement job IDs, runtime output paths, aggregator commands, validator commands, lock paths, log paths, retry ledger paths, terminal accounting, post-job aggregation receipts, and the exactly one local lightweight packet commit policy from the executor plan and runtime receipts.

```text
controller_context.json
controller_ledger.csv
controller_bootstrap_snapshot.md
implementation_snapshot.md
finalizer_state.json
mapper_report_draft.md
architecture_delta_draft.md
mapper_report_final.md
architecture_delta_final.md
result.md
completion_check.md
review_request.md
MANIFEST.md
controller_report.md
```

The controller may create exactly one local lightweight final packet commit. It must not write `review.md`, push, package/upload validation, claim hosted metrics, promote or stop a route, start M11, or modify historical M08/M09/M10 evidence.
## Executor Worker Contract

All executors must read `AGENTS.md`, the current canonical M10 follow-up prompt, this executor plan, the planning review, the Slurm skill when relevant, and the exact evidence/code paths declared for their wave. Executors remain within their `read_scope`/`write_scope`, use isolated branches/worktrees/result/runtime/log/lock paths, write the required completion receipt, and never merge their own branch.

F1 performs only fingerprint validation, inherited runtime evaluation, all-checkpoint challenge-facing selection, D2/D3 interventions, subgroup/help-harm aggregation, and strict validator fixtures. It must not train or edit implementation.

F2 performs only first-party Cine implementation, tests, configs, entrypoints, jobs, deterministic print-contracts, and freeze-receipt preparation. It must prove with tests that direct velocity-as-displacement, binary/frame0 fallback, proxy SyN, pair-as-case rate, no selected-checkpoint reload, missing random-init control, and temporal output without passed registration all fail closed. It must not submit formal training.

F3 validates the F2 freeze receipt, runs compute preflight, trains/evaluates the adapted and random-initialized controls, selects and reloads the source checkpoint, trains/evaluates registration, runs real SyN, applies the case-level gate, and conditionally trains/evaluates the temporal dictionary. It writes only new follow-up runtime/evidence paths and may not alter code/config/jobs.

Allowed executor completion tokens are those declared in the plan. `READY_FOR_CONTROLLER_MERGE` means only the controller may merge that wave; it is not scientific approval. Pending/running/accounting states are `NEEDS_MONITOR`, never completion.
## Mapper Contract

Use `.agents/skills/care-mapper/SKILL.md`. For system-level planning and mapping, dynamically resolve the predecessor baseline from `wiki/current_state.yaml` and `wiki/history/`, then read `wiki/history/COMPARISON.md`, the predecessor README/COMPONENTS files, and the relevant predecessor component files such as `wiki/history/<predecessor>/components/*.md` before writing mapper outputs. After F2 merge, create a draft mapping of the new Cine implementation and mark runtime evidence unverified. After F3 terminal aggregation, rerun mapper final against the frozen hashes and current evidence. Update root `wiki/README.md`, `wiki/MODEL.md`, `wiki/EXECUTION.md`, `wiki/COMPONENTS.csv`, `wiki/LINEAGE.md`, `wiki/architecture.yaml`, and generated current/gap/execution figures. Add a `wiki/history/M10/` candidate snapshot marked `candidate_unreviewed` and `review_token: NOT_REVIEWED`; do not change `wiki/current_state.yaml` from M09 before independent runtime review and a later reconciliation task. Do not modify model code, inspect heavy runtime artifacts, write `review.md`, or make promotion/negative-route decisions.
