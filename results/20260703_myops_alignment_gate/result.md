# Result 20260703 MyoPS Alignment Gate

self_assessed_status: `STOP`
route_decision: `STOP_ALIGNMENT_NOT_PRIMARY`
role: executor
review_required: true
controller_task: `prompts/tasks/20260703_hardmode_goal.md`

## 执行摘要

完成了 complete C0+LGE+T2 fold0 只读/CPU alignment diagnosis。诊断使用 raw LGE/C0/T2 header、slice correspondence、center-of-mass、mutual information/edge proxies，并和既有 nnU-Net fold0 pathology failure 指标关联。

结论：`STOP_ALIGNMENT_NOT_PRIMARY`，controlled next state 为 `STOP`。当前 complete-case evidence 不支持 cross-sequence mismatch 是主要 pathology failure driver，因此没有强行执行 slice/TPS/BSpline/Demons/feature-level warp，也没有训练、fold expansion、validation packaging、upload、label mapping 或 evaluator 修改。

## 读取文件

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_ROLES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CONTROLLER_TASK_PROTOCOL.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_myops_alignment_gate.md`
- `results/20260703_myops_audit/review.md`
- `results/20260703_myops_fp_control/review.md`
- `results/20260703_myops_srr_propose_refine/review.md`
- `results/20260629_rescue_goal/final_status.md`
- `/users/a/e/aereinh/CARE/data/benchmarks/protocol/splits_MyoPS.json`
- `/users/a/e/aereinh/CARE/results/diagnostics/care_myocardium/laneA_myops/myops_modality_center_case_metrics.csv`
- `/users/a/e/aereinh/CARE/data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr`
- `/users/a/e/aereinh/CARE/results/predictions/nnUNet501/fold_0`
- `/users/a/e/aereinh/CARE/data/CARE_Challenge/MyoPS_train`

## 修改文件

- `scripts/evaluation/myops_alignment_gate_20260703.py`
- `results/20260703_myops_alignment_gate/result.md`
- `results/20260703_myops_alignment_gate/MANIFEST.md`
- `results/20260703_myops_alignment_gate/alignment_diagnosis.md`
- `results/20260703_myops_alignment_gate/registration_metrics.csv`
- `results/20260703_myops_alignment_gate/warp_sanity.csv`
- `results/20260703_myops_alignment_gate/subgroup_metrics.csv`
- `results/20260703_myops_alignment_gate/component_hd_by_case.csv`
- `results/20260703_myops_alignment_gate/visual_sanity_index.md`
- `results/20260703_myops_alignment_gate/failure_interpretation.md`
- `results/20260703_myops_alignment_gate/command_transcript.md`

## 运行命令

- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/evaluation/myops_alignment_gate_20260703.py` -> exit `0`, elapsed `9.26s`

## 关键证据

- complete C0+LGE+T2 cases: `16`.
- mismatch/failure valid pairs: `16`.
- correlation rows: `results/20260703_myops_alignment_gate/registration_metrics.csv`.
- pathology subgroup metrics: `results/20260703_myops_alignment_gate/subgroup_metrics.csv`.
- case-level HD/component/remote-FP metrics: `results/20260703_myops_alignment_gate/component_hd_by_case.csv`.

## 停止原因

`STOP_ALIGNMENT_NOT_PRIMARY`: alignment mismatch did not show the required positive relationship with pathology failure, so harder registration candidates were not forced.

claim.alignment_diagnosis: complete-case raw C0/LGE/T2 geometry and intensity alignment proxies were computed and compared with existing fold0 pathology failures.
claim.no_training_or_upload: no training, fold expansion, label mapping/evaluator change, validation package, upload, commit, or push was performed.
claim.next_state: executor stops at controlled state `STOP` with route decision `STOP_ALIGNMENT_NOT_PRIMARY` pending separate audit.
