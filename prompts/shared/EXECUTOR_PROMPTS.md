# SRR-v3 Executor Prompts

Copy exactly one section into the main Codex executor/controller session. The executor must commit locally and stop. The user manually pushes.

## Local commit rule for every milestone

At goal completion, the executor must create one local commit containing every small file needed for the separate reviewer to inspect the milestone. A milestone goal is not complete merely because files exist locally under an ignored `results/20??????_*` directory; the reviewer must be able to recover the required evidence from git after the user pushes the commit.

The commit must include the milestone required outputs, `result.md`, `completion_check.md`, `review_request.md`, `MANIFEST.md`, small Markdown/CSV/JSON evidence tables, and any small first-party helper/source/config files needed to reproduce or interpret the evidence. Use `git add -f` for ignored `results/20??????_*` milestone packets. If any required review evidence is intentionally not committed, the executor must state the exact reason in `result.md`, `completion_check.md`, and `MANIFEST.md`; otherwise omission of necessary review evidence is a protocol violation.

Do not commit checkpoints, NIfTI predictions, upload packages, large logs, raw data, secrets, environment dumps, or whole runtime result trees. Do not push; the user manually pushes.

## Global executor rule

```text
这是单个 milestone 的 executor/controller session。只执行当前 milestone。goal 完成前必须用 git add -f 提交供 reviewer 审阅所需的全部轻量证据文件；只把文件留在本地 ignored results 目录里不算完成，因为 reviewer 在用户 push 后必须能从 git 中恢复证据。提交范围包括 required outputs、result.md、completion_check.md、review_request.md、MANIFEST.md、小型 Markdown/CSV/JSON 证据表，以及生成或解释这些证据所需的小型 first-party helper/source/config 文件；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets、environment dumps 或整个 runtime result tree。如果任何 reviewer 必需证据不提交，必须在 result.md、completion_check.md 和 MANIFEST.md 写清具体原因，否则视为 protocol violation。不要 push，由用户手动 push。随后停止；不要写 review.md、不要批准自己、不要启动下一个 milestone。必须由另一个独立只读 Codex reviewer 写 review.md 并给出 audited-go 后，才允许进入下一 milestone。
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

## M6 executor: MyoPS co-equal SRR/segmentation decode-refiner repair

```text
只执行 M6：MyoPS co-equal SRR/segmentation decode-refiner repair。M5 是 Cine 副线，不是 M6 前置条件。开始前必须确认 results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md 存在且包含 M4_AUDITED_GO，否则停止并写 M6_BLOCKED_BY_M4。

这是 MyoPS 主线的 implementation/runtime-repair milestone，不是 full fold，不是 route promotion，不是 validation packaging/upload。M6 的科学前提是：接受 nnU-Net 或其他强分割模型作为安全分割分支和上下文来源，但不能让 SRR 退化成可有可无的后处理。SRR 分支、分割分支、loss function、proposal/refiner 必须在机制中有同等地位。closed-gate fallback 只是安全刹车，不是目标路线；最终系统必须能报告 SRR 分支何时赢、何时输、为何被仲裁器采用或拒绝。

背景证据来自 M3/M4：M3 最小有效训练通过但同 split 指标伤害 nnU-Net；M4 证明 closed-gate identity 是中性的，no-anchor 很伤，M3 trained gate 几乎关闭但 decode/proposal/refinement 仍会改标签，说明当前主要问题不是 fallback 本身，而是 proposal/refinement/decode 与分支仲裁没有被正确约束。M6 只修这个问题，不重新跑 M3，也不把 M4 结果包装成成功路线。

必须实现或重构以下机制，并用小规模 synthetic + explicit real-case smoke 证明它们真的运行：

1. Co-equal branch arbitration：把分割模型分支和 SRR 分支作为两个同级候选，而不是“nnU-Net 最终答案 + SRR 小修补”。仲裁器必须输出 per-class/per-case 的 anchor_weight、srr_weight、refiner_weight、chosen_source 或等价字段。SRR 分支必须能在 synthetic known-error / high-uncertainty 区域被选择；分割分支必须能在 SRR 证据低质时被选择。
2. Decode/gate consistency：如果仲裁器选择分割分支或 gate/refiner mask 关闭，最终标签必须精确等于分割分支；不允许出现 M4 中那种 gate 近零但 pathology-aware decode 仍大量改标签的隐藏路径。所有 label delta 都必须能追溯到显式的 SRR arbitration/refiner mask。
3. Loss/refiner centrality：loss function 必须显式包含 SRR 分支监督、分割分支保持项、仲裁一致性项、bounded correction 项、component/remote-FP 惩罚项、no-T2 edema 条件项和 local refiner ROI 项。不要只把 loss/refiner 当辅助日志；必须导出每一项的非空数值、梯度或 one-step update sanity。
4. Refiner as mechanism：local refiner 必须消费 SRR proposal、分割分支 logits/probabilities、anatomy prior、prototype/dictionary features 和 uncertainty/context，并输出 bounded local correction。必须证明 crop 是 bounded，不是 full-volume residual；必须导出 scar/edema crop ratio、residual magnitude、component/remote-FP proxy。
5. SRR contribution floor without unsafe forcing：不能强行让 SRR 改所有 case，但在 correction-positive synthetic/real smoke 中，SRR contribution 不能全为 0；在 no-T2 case 中，edema 仍必须全链路安全。
6. Provenance and strict validation：所有 smoke 必须记录 checkpoint/source status、selected case ids、eval case ids、patch shape、commands、code paths、artifact paths；strict validator 必须 fail closed 于 claim-only packet、hidden-decode-delta packet、SRR-zero-contribution packet、no-T2 edema unsafe packet、full-volume-refiner packet。

结果写入 results/20260705_srr_v3_m6_myops_coequal_decode_refiner_repair/，必须写齐以下轻量文件：

result.md
coequal_repair_contract.md
code_diff_summary.md
m4_failure_mapping.csv
branch_arbitration_sanity.csv
decode_gate_consistency_sanity.csv
loss_refiner_component_sanity.csv
refiner_roi_component_sanity.csv
no_t2_safety_sanity.csv
strict_validator_report.md
unit_test_report.md
completion_check.md
review_request.md
MANIFEST.md

completion_check.md 只能写 M6_READY_FOR_REVIEW、M6_NEEDS_REVISION 或 M6_NEEDS_EVIDENCE。不能 mark ready 的情况包括：SRR 分支贡献在所有 correction-positive sanity 中为 0；gate/refiner mask 关闭时最终标签仍改变；loss/refiner 只有自然语言说明没有数值/梯度/one-step sanity；local refiner 证据是 full-volume；no-T2 edema 出现非零 decode；strict validator 不能 fail closed known-bad packet。

完成后用 git add -f 提交 M6 packet 供 reviewer 审阅所需的全部轻量文件和必要 helper/source/config；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets、environment dumps 或整个 runtime result tree；不要 push，由用户手动 push。不要写 review.md，不要批准自己，不要启动 M7。M6 是否给 M6_AUDITED_GO 由独立 reviewer 决定。
```
