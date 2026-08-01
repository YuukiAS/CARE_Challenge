---
task_key: 20260801_care_four_lane_evidence_reconciliation
task_kind: audit
task_type: post_training_model_fidelity_and_outer_evidence_reconciliation
status: AUTHORIZED
risk_level: high
route_change: false
scientific_decision_scope: stop_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: true
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
review_required: false
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: true
new_training_authorized: false
new_slurm_job_authorized: false
existing_interactive_allocation_only: true
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
---

# CARE 四模型结果纠偏与最后信息闭合 Controller

## Execution Contract

本任务只做一次低成本、不会重新训练模型的结果纠偏。它必须回答：M0R、M1、M2、M3 当前哪些结论是真正的科学结果，哪些只是实现降级或评价遗漏；尤其要补齐 M2 在真正未见 outer 病例上的结果，并把 M0R 与同病例 stock nnU-Net 做严格比较。

本任务不得重新训练 M0R、M1、M2、M3，不得新增模型，不得提交任何新 Slurm job，不得访问 official validation，不得上传 Docker。

当前已知但必须机器复核的边界：

```text
latest main before this task:
d645614ea3427ff336b22d1f485fdc2c5dd5d0a3

old repository decision:
SCAR_ONLY_CANDIDATE_READY

reported M0R outer:
scar Dice ≈ 0.6500
pure-edema Dice ≈ 0.4340

same-case stock fold2/fold3 means from prior audit:
scar Dice ≈ 0.6720
pure-edema Dice ≈ 0.4746

M2 selected inner checkpoints:
scar step4500
pure-edema step2500
```

旧 `SCAR_ONLY_CANDIDATE_READY` 不能被直接继承；只有在本任务的 same-case stock comparison 和 candidate gates 通过后才可保留。

## Controller Prompt

### 1. Bootstrap

```bash
cd /users/a/e/aereinh/CARE
source /users/a/e/aereinh/CARE/.care-codex-env.sh
source /users/a/e/aereinh/CARE/env_nnunet.sh
export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:$PATH

git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

若 main 落后且工作树干净：

```bash
git pull --ff-only origin main
```

不得 reset、clean、覆盖或 stash 用户未提交改动。不得写 `/overflow/htzhu/CARE`。

### 2. Required reading and visual gate

完整读取：

```text
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
AGENTS.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/care-mapper/SKILL.md
```

视觉读取 ChatGPT Project 背景中的 `SRR-v2`、`SRR-v2.5`、`SRR-v3`，在 `controller_context.json` 中记录：

```text
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: PASS
recovered_route_objective: modality-specific evidence, pathology-specific authority, soft anatomy context, lesion proposal/refinement, negative-space accounting, and baseline safety
```

### 3. Frozen inputs

读取：

```text
results/20260801_care_target_domain_race_gap_closure/**
results/20260801_care_target_domain_pathology_specialist_race/m0_td_nnunet/**
results/20260731_care_qif_v2_signal_audit/**
results/20260730_care_failure_forensics_deep_research_packet/**
```

冻结并记录 SHA256：

```text
M0R fold2/fold3 selected checkpoints
M1 fold2/fold3 selected checkpoints
M2 fold2/fold3 selected checkpoints
M3 fold2/fold3 selected checkpoints
fold2/fold3 stock nnU-Net checkpoints
split_receipt_copy.json
all evaluation scripts used in this task
```

不得改变病例 membership、threshold、decode 或 checkpoint。

### 4. Metric correction before any conclusion

实现独立 first-party evaluator：

```text
scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py
scripts/validation/validate_four_lane_evidence_reconciliation.py
```

评价必须修复以下问题：

1. HD95 和 exact HD 使用 NIfTI/nnU-Net properties 中真实 physical spacing，单位 mm，不得写 `vox` 冒充 mm。
2. small lesion 固定为物理体积 `<1000 mm3`，不得使用 `<100 voxels`。
3. 每个病例、每个病种同时报告 Dice、HD95 mm、exact HD mm、precision、sensitivity、lesion recall、small-lesion recall、component count、remote-FP count/volume、blood-pool-adjacent FP、volume ratio。
4. remote FP 距离使用物理距离 `>10 mm`。
5. 评价可使用 GT anatomy 做分析分层，但必须明确这是 evaluation-only，不得进入模型推理。
6. 空 GT 与非空 GT 的 denominator 语义分别报告，不得混合抬高分数。
7. 同一病例必须使用完全相同的原始几何和 label mapping。

### 5. M0R truth audit

对 fold2+fold3 的 32 个 outer 病例，分别运行：

```text
stock nnU-Net
M0R scar step3500
M0R edema step4000
```

必须输出 same-case delta：

```text
M0R minus stock Dice
M0R minus stock HD95
M0R minus stock sensitivity/precision
help/harm/neutral
Case3008
Case3009
Case2019
Case2034
Case2021
```

同时审计 inner privilege：对每个 inner-selection case，机器证明它是否出现在用于初始化 M0R 的 stock checkpoint 原训练 fold 中，并输出：

```text
inner_case_seen_by_stock_training
stock_inner_metrics
M0R_inner_metrics
M0R_minus_stock_inner
```

若 inner 病例被 stock checkpoint 见过，则 M0R 的 inner 0.888/0.792 只能解释为 contaminated development selection，不得作为跨模型公平选择证据。

### 6. M2 mandatory outer evaluation

M2 是唯一必须补 outer 的非 M0R lane。使用已经冻结的：

```text
scar step4500
pure-edema step2500
```

在相同 fold2+fold3 outer 32 病例上 deterministic replay，一次完成，不得调 threshold 或换 checkpoint。

必须与同病例 stock 和 M0R 比较，并逐例报告五个 sentinel cases。

M2 只有同时满足以下条件，才可写 `M2_OUTER_CANDIDATE_WORTH_PACKAGING`：

```text
scar Dice >= stock scar Dice + 0.02
scar HD95 <= stock + 2 mm
scar harm fraction < 0.40
Case3008 and Case3009 neither degrades by more than 0.03
```

Edema 单独判断，不得用 scar 成功掩盖：

```text
pure-edema Dice >= stock + 0.02
sensitivity >= stock + 0.03
precision >= stock - 0.05
HD95 <= stock + 2 mm
harm fraction < 0.40
```

### 7. M1 and M3 fidelity classification; no retraining

M1/M3 不再消耗训练资源，只做代码与合同逐项绑定。

M1 必须核对：

```text
是否真实使用 official CMFF/MPC/pathology inclusiveness
是否使用 hard argmax anatomy mask
scar target 与 injury/pure-edema target 是否符合论文和 CARE 合同
是否有病灶平衡采样、空间/强度增强和 full-volume reconstruction
实际输入尺寸、loss 和 optimizer
```

终态只能写：

```text
M1_FAITHFUL_NEGATIVE
M1_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC
```

M3 必须核对：

```text
stock encoder/decoder是否冻结
是否实现 blueprint 的 Dice/Focal/component-Tversky/MIL/remote-FP/boundary-distance losses
hard-negative mask 是否真实进入 loss
是否使用 blueprint patch/batch manifests
是否只有浅层 BCE heads
```

终态只能写：

```text
M3_FAITHFUL_NEGATIVE
M3_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC
```

根据当前代码，若核心结构和 loss 未实现，不得把 0.0229/0.0 写成 CARE-TDS 科学失败。

### 8. Required outputs

只允许写：

```text
scripts/evaluation/four_lane_reconciliation/**
scripts/validation/validate_four_lane_evidence_reconciliation.py
tests/four_lane_reconciliation/**
results/20260801_care_four_lane_evidence_reconciliation/**
prompts/routes/handoffs/CURRENT.md
wiki/README.md
```

必须生成：

```text
controller_context.json
frozen_asset_manifest.json
metric_contract.json
inner_stock_privilege_audit.csv
m0r_vs_stock_outer_casewise.csv
m0r_vs_stock_outer_summary.csv
m2_outer_casewise.csv
m2_vs_stock_outer_summary.csv
sentinel_case_comparison.csv
m1_fidelity_audit.json
m3_fidelity_audit.json
four_lane_scientific_interpretation.md
strict_validator_report.json
known_bad_report.json
controller_report.md
completion_check.md
MANIFEST.md
notification_brief.json
```

### 9. Allowed scientific decisions

只允许：

```text
FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE
M2_OUTER_CANDIDATE_WORTH_PACKAGING
OPERATIONALLY_BLOCKED_CHECKPOINT_OR_RUNTIME
```

M0R 若低于 stock，必须明确撤销 `SCAR_ONLY_CANDIDATE_READY`。M1/M3 implementation-negative 不能阻止任务终态，但必须诚实记录。

### 10. Strict known-bad

至少覆盖：

```text
HD vox mislabeled as mm
small lesion defined in voxels
M0R compared without same-case stock
inner stock-training privilege ignored
M2 omitted from outer because it lost inner selection
M2 checkpoint/threshold changed after outer access
M1 simplified wrapper called faithful negative
M3 shallow BCE heads called faithful CARE-TDS
GT anatomy enters inference
outer-driven source selection
empty-GT cases inflate pathology mean
validator PASS substitutes scientific gate
CURRENT/wiki retain scar-only candidate after same-case negative
new training or new Slurm job launched
notify before push or nonterminal notify
```

### 11. Compute

优先复用现有 RUNNING interactive allocation `61220581`，但先以 `scontrol show job` 确认仍存在且可用。只允许 `srun --jobid=61220581 --overlap` 做冻结 checkpoint inference。

严格禁止：

```text
salloc
sbatch
新训练
checkpoint修改
```

若 interactive 已结束，可在主机 CPU 做代码审计；若 M2 outer GPU inference 无法完成，则终态为 `OPERATIONALLY_BLOCKED_CHECKPOINT_OR_RUNTIME`，不得创建新 job。

### 12. Commit, push, notifier

全部评价和 validator 完成后：

```bash
exec 9>/users/a/e/aereinh/.care-main-push.lock
flock -x 9

git fetch origin main
git rebase origin/main
./envs/env_CARE/bin/python scripts/validation/validate_four_lane_evidence_reconciliation.py --phase final
git diff --check
git commit -m "audit: reconcile four-lane target-domain evidence"
git push origin HEAD:main
```

禁止 force push，禁止推送 task/codex branch。验证 local SHA == remote main SHA。

随后写终态 `notification_brief.json` 并执行：

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

若 notifier receipt 被跟踪，commit/push main并再次验证远端 SHA。

## Executor Worker Contract

Executor只执行冻结 checkpoint评价、代码真实性审计、指标修复和证据写入。不得重新训练或自行设计模型。

## Mapper Contract

Mapper只读追踪每条 lane 的真实 `input -> architecture -> loss -> checkpoint -> inference -> final labels`，并核对 CURRENT/wiki 是否与纠偏结果一致。