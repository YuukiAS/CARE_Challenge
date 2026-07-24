# Batch10 Controller Terminal Decision

这次修复后的证据说明：当前 CARE-MMRD 非 nnU-Net 路线能完成公平推理、校准选择、共同预处理空间融合和安全回退，但在保留的 audit 病例上仍没有稳定达到同划分 nnU-Net 基线。这个结果重要，因为继续短训或包装 Docker 候选会把一个未过安全门的候选推进到竞赛路线；下一步应停止这条 Batch10 CARE-MMRD 竞赛路线，保留证据供后续人工重新设计。当前未授权 validation upload、Docker upload、hosted 验证、hosted 成绩声明、Batch11 和旧 Batch9 Wave6 恢复。

controller_verification_decision: `VERIFIED_COMPLETE`
final_decision: `STOP_CARE_MMRD_COMPETITION_ROUTE`
selected_candidate: `distill_epoch25_two_seed_mean` / `raw_argmax`

**Audit Metrics**

| pathology | audit Dice | delta vs nnU-Net | audit HD95 | audit harm | remote FP mean mm3 | full44 Dice | empty audit predictions |
|---|---:|---:|---:|---:|---:|---:|---:|
| scar | 0.608330 | -0.022067 | 14.392203 | 15 | 808.183 | 0.545553 | 0 |
| edema | 0.390442 | -0.028956 | 21.032770 | 6 | 0.000 | 0.376217 | 0 |

near_baseline_gate_status: `FAIL`
training_authorized: `False`
no_t2_edema_predicted_voxels: `0`

**Evidence Paths**

- `results/20260724_care_myops_batch10_deadline_rescue/strict_validator_report.json`
- `results/20260724_care_myops_batch10_deadline_rescue/known_bad_report.json`
- `results/20260724_care_myops_batch10_deadline_rescue/near_baseline_gate.json`
- `results/20260724_care_myops_batch10_deadline_rescue/wave2_fair_reevaluation_receipt.json`
- `results/20260724_care_myops_batch10_deadline_rescue/wave3_ensemble_postprocess_receipt.json`
- `results/20260724_care_myops_batch10_deadline_rescue/paired_spatial_fiducial_checks.csv`
- `results/20260724_care_myops_batch10_deadline_rescue/docker_feasibility_probe.json`
- `results/20260724_care_myops_batch10_deadline_rescue/gap_register.csv`
- `results/20260724_care_myops_batch10_deadline_rescue/controller_ledger.csv`
