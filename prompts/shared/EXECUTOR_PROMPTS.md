# SRR-v3 Executor Prompts

Copy exactly one section into the main Codex executor/controller session. The executor must commit locally and stop. The user manually pushes.

## Local commit rule for every milestone

At goal completion, the executor must create one local commit containing every small file needed for the separate reviewer to inspect the milestone. This includes the milestone required outputs, `completion_check.md`, `review_request.md`, `MANIFEST.md`, small Markdown/CSV/JSON evidence tables, and any small first-party helper/source/config files needed to reproduce or interpret the evidence. Use `git add -f` for ignored `results/20??????_*` milestone packets. Do not commit checkpoints, NIfTI predictions, upload packages, large logs, raw data, secrets, environment dumps, or whole runtime result trees. Do not push; the user manually pushes.

## Global executor rule

```text
这是单个 milestone 的 executor/controller session。只执行当前 milestone。写完 required outputs、completion_check.md、review_request.md 和 MANIFEST.md 后，用 git add -f 提交供 reviewer 审阅所需的全部轻量证据文件，包括 required outputs、小型 Markdown/CSV/JSON 证据表，以及生成或解释这些证据所需的小型 first-party helper/source/config 文件；不要提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets、environment dumps 或整个 runtime result tree。不要 push，由用户手动 push。随后停止；不要写 review.md、不要批准自己、不要启动下一个 milestone。必须由另一个独立只读 Codex reviewer 写 review.md 并给出 audited-go 后，才允许进入下一 milestone。
```

## M0 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md。这是架构契约 milestone，不训练、不改模型、不跑后续 milestone。先读取 handoff hard-gate repair review、SRR-v2.5 evidence supplement audit、HANDOFF_GATE_POLICY、GPT_HARD_GATE_PROMPT、MILESTONE_REVIEW_PROTOCOL；确认 hard-gate repair 是 AUDITED_GO。然后在 results/20260705_srr_v3_m0_architecture_master_contract/ 写齐 required outputs、completion_check.md、review_request.md 和 MANIFEST.md。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M1。
```

## M1 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md。开始前必须确认 results/20260705_srr_v3_m0_architecture_master_contract/review.md 存在且包含 M0_AUDITED_GO，否则停止。目标是补足运行时证据，不训练新模型：导出 gate open-rate、bounded delta、gate*delta、decode label delta、anchor confidence、prototype T2-present coverage、anchor/component alignment、no-T2 safety。结果写入 results/20260705_srr_v3_m1_runtime_instrumentation_gate/。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M2。
```

## M2 executor

```text
只执行 prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md。开始前必须确认 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md 存在且包含 M1_AUDITED_GO，否则停止。目标是修复 MyoPS 运行时架构缺口，只允许小规模 smoke，不允许 full-fold training：closed gate 要精确复现 nnU-Net，同时要有 correction-positive gate opening sanity；strong encoder/context 要有现实可运行证据；prototype bank 必须包含 T2-present edema 正负证据；proposal/refinement 必须有 bounded local ROI 证据；no-T2 edema 必须端到端安全。结果写入 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/。完成后用 git add -f 提交该 milestone 供 reviewer 审阅所需的全部轻量文件：required outputs、小型 Markdown/CSV/JSON 证据、以及必要的小型 first-party helper/source/config；不要提交重型 runtime 产物或整个 result tree；不要 push，由用户手动 push。不要写 review.md，不要启动 M3。
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
