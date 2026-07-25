# SCR-R1 RC1 Controller Terminal Report

这次本地执行已经结束：CARE-SRR-Cascade 的正式训练、评价、审计、严格验证和 Mapper/wiki 收尾都已完成；结果不是可上传的自定义模型，而是 scar 和 edema 都回退到现有 nnU-Net baseline。原因很具体：两个自定义候选在 audit 的 exact-HD 门上失败，因此不能包装成 custom package，也不能声称 leaderboard 改进。当前只做了本地提交，没有 push、上传、扩 fold 或新 Cine 训练。

## Controller Decision

controller_verification_decision: `VERIFIED_COMPLETE`

- method: `CARE-SRR-Cascade`
- execution: `SCR-R1`
- repair scope: `SCR-R1-RC1`
- runtime closure commit: `31d4ffed30d0a0caa775cb064d5c5945847c5c51`
- remote state before final local commits: `origin/main = c0b6b5b0fe2000b3b7b19e5d4c5dc0838df8b4e2`
- push/upload: not performed

## Final Scientific State

- scar: `FALLBACK_TO_NNUNET`; selected audit-evidence candidate `control_two_seed_probability_mean_derived_bounded_channel_correction`; failed gate `exact_HD_delta_max`.
- edema: `FALLBACK_TO_NNUNET`; selected audit-evidence candidate `control_seed20260724`; failed gate `exact_HD_delta_max`.
- final token: `NO_CUSTOM_RESCUE_USE_BASELINE_ONLY`.
- W5 package/Docker dry-run: skipped by contract because no custom pathology passed audit.

## Terminal Accounting

- Formal W3 credited jobs: `60570582`, `60570583`, `60570648`, `60570649`; all `COMPLETED 0:0`.
- Race losers / superseded A100 attempts: `60570584`, `60570585`, `60571937`, `60571938`; all controller-cancelled with zero formal credit.
- W4 evaluator: `60576153 COMPLETED 0:0`.
- W4 afterany finalizer: `60576158 COMPLETED 0:0`.
- `squeue` for the SCR-R1 job set returned no active rows at final refresh.

## Evidence Checked

- W3 accounting: `results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/formal_terminal_accounting_v2.json`
- W4 aggregation: `results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/w4_aggregation_status_v2.json`
- Strict validator: `results/20260724_care_myops_srr_cascade_submission_rescue/strict_validator_report_v2.json`
- Known-bad report: `results/20260724_care_myops_srr_cascade_submission_rescue/real_known_bad_report_terminal_v2.json`
- Finalizer state: `results/20260724_care_myops_srr_cascade_submission_rescue/finalizer_state.json`
- Mapper report: `results/20260724_care_myops_srr_cascade_submission_rescue/mapper_report_final.md`

## Local Verification

- `git fetch --all --prune`: completed before final verification.
- `git rev-parse HEAD` and `git rev-parse origin/main`: both were `c0b6b5b0fe2000b3b7b19e5d4c5dc0838df8b4e2` before local commits.
- `git merge-base --is-ancestor 6b9834c6f20416392a540535056c7196a4c429f3 origin/main`: pass.
- `scripts/evaluation/aggregate_care_srr_cascade_w4.py --result-root results/20260724_care_myops_srr_cascade_submission_rescue`: `PASS_READY_FOR_STRICT_VALIDATOR`.
- `scripts/evaluation/validate_care_srr_cascade_packet.py --packet-root results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1`: `PASS`.
- `scripts/architecture/validate_care_architecture_wiki.py --strict`: pass.
- `pytest tests/care_mm/test_care_srr_cascade_runtime_rc1.py tests/care_mm/test_care_srr_cascade_rescue.py -q`: `25 passed`.

## Boundaries

- Calibration used only the six contract candidates per pathology.
- Audit was used only after calibration freeze, not for choosing seeds, checkpoint, ensemble, pathology, or parameters.
- Formal preflight gate follows the amended rule: any compatible GPU partition preflight PASS is sufficient.
- No Batch11, no SCR-R2, no old Wave6 restore, no fold expansion, no new Cine training, no validation upload, no Docker upload, and no push.
