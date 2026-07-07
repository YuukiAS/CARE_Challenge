# SRR-v3 Executor Prompts

Copy exactly one section into the main Codex executor/controller session. The executor must commit locally and stop. The user manually pushes.

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

## M7 executor follow-up 1 (continued): reviewer-blocker repair

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
