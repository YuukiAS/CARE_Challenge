# Controller Report

这次任务完成了四条模型线的低成本证据纠偏：没有重新训练，没有启动新 Slurm 作业，也没有访问 official validation。重新按同病例 stock nnU-Net 做外部病例比较后，M0R 的 scar 和 edema 都没有超过 stock；M2 虽然补做了 outer replay，但 scar 明显低于 stock，edema 也没有达到候选门槛且损害病例比例过高。因此旧的 scar-only 候选说法应撤销，当前只把本地证据归档为“纠偏后无可打包候选”，下一步必须回到 Planner，而不是继续调阈值、上传 Docker 或声称 hosted validation 指标。

## Evidence Summary

The evaluator used frozen fold2/fold3 checkpoints and fixed case membership from `results/20260801_care_target_domain_race_gap_closure/split_receipt_copy.json`.

| comparison | pathology | Dice delta vs stock | HD95 delta mm | gate |
| --- | --- | ---: | ---: | --- |
| M0R selected | scar | -0.0020118904817150174 | 0.39678911900855596 | revoke old candidate |
| M0R selected | pure_edema | -0.030114178203399733 | 2.385155858141605 | revoke old candidate |
| M2 selected | scar | -0.05011471399535905 | -1.789971749201964 | fail |
| M2 selected | pure_edema | 0.018926404811234976 | -1.3052110167901532 | fail |

The physical metric contract is recorded in `metric_contract.json`: HD95 and exact HD are in millimetres from nnU-Net preprocessing properties, remote false positives use a `>10 mm` physical-distance threshold, and small lesions are components with physical volume `<1000 mm3`.

## Fidelity Classification

M1 is `M1_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC`: the current adapter uses pinned MyoPS-Net components, but it keeps hard argmax anatomy masking and lacks the full official CMFF/MPC/pathology-inclusiveness, lesion-balanced sampling, augmentation, and full-volume training contract.

M3 is `M3_IMPLEMENTATION_NEGATIVE_NOT_SCIENTIFIC`: the current implementation freezes the stock adapter and adds shallow BCE heads with limited containment losses; it does not implement the blueprint's Dice/Focal/component-Tversky/MIL/remote-FP/boundary-distance losses or hard-negative loss path.

## Validation

Commands completed:

```bash
./envs/env_CARE/bin/python -m pytest -q tests/four_lane_reconciliation/test_metric_contract.py
./envs/env_CARE/bin/python -m py_compile scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py scripts/validation/validate_four_lane_evidence_reconciliation.py
srun --jobid=61220581 --overlap --ntasks=1 /users/a/e/aereinh/CARE/envs/env_CARE/bin/python /users/a/e/aereinh/CARE/scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py
```

No new training was launched. No new Slurm job was submitted. The existing allocation `61220581` was verified as RUNNING on `htzhulab / g1807htzh01` before inference reuse.

## Machine Fields

controller_verification_decision: VERIFIED_COMPLETE
controller_run_status: complete
operational_completion_status: complete
experiment_adequacy_decision: frozen_reconciliation_complete_no_retraining
contract_compliance_status: PASS
required_outputs_complete: PASS
validators_passed: PASS_AFTER_FINAL_VALIDATOR
all_jobs_terminal: not_applicable_existing_allocation_reused_for_inference_only
aggregation_complete: PASS
scientific_decision: FOUR_LANE_EVIDENCE_CORRECTED_NO_CANDIDATE
route_promotion_decision: not_authorized
route_negative_decision: local_no_candidate_return_to_planner
scientific_resolution_status: local_reconciliation_complete_planner_decision_required
diagnostic_publication_decision: lightweight_main_push_authorized
git_commit_decision: auto_commit_authorized_after_validator_pass
git_push_decision: auto_push_origin_main_authorized_after_commit
published_files: results/20260801_care_four_lane_evidence_reconciliation, scripts/evaluation/four_lane_reconciliation, scripts/validation/validate_four_lane_evidence_reconciliation.py, tests/four_lane_reconciliation, prompts/routes/handoffs/CURRENT.md, wiki/README.md
blocked_actions: new_training; new_slurm_job; validation_upload; docker_upload; hosted_metric_claim; force_push; task_branch_push
next_required_action: RETURN_TO_PLANNER
reason_if_not_published: none
reason_if_no_route_promotion: same-case frozen outer evidence did not beat stock and M2 gates failed
