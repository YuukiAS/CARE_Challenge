# Route C Round03 Controller Report

controller_run_status: COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PASS
route_promotion_decision: NOT_REVIEWED
route_negative_decision: NOT_REVIEWED
scientific_resolution_status: AWAITING_REVIEW
diagnostic_publication_decision: LOCAL_PACKET_COMMITTED_FOR_REVIEW
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: PUSH_AUTHORIZED_BY_USER_FOR_THIS_REPAIR

## Reviewer Revision Repair

Inherited blocker, verbatim: Route C R1 requires `positive_negative_prototype_swap` to be a known-bad control, and it must be detected as harmful or semantically invalid. The previous `intervention_controls.csv` had 88 `positive_negative_prototype_swap` rows with `expected_behavior=known_bad_detected`, `observed_behavior=KNOWN_BAD_NOT_DETECTED`, and `pass=False`, but `validate_r1_packet.py` and `validate_final_packet.py` still exited 0. This was a semantic validator fail-open, not an adequate negative, not monitor, not undertrained, and not evidence-complete.

The repair fixes the real R1 graph-node intervention rather than editing the CSV. Historical D2/D3 proposal dictionaries use unequal positive/negative bank sizes, so the old swap silently skipped the real buffers. The R1 runner now performs a shape-aware positive/negative prototype-bank swap by repeat/truncate resizing to the destination bank shape and normalizing before writing the real model buffers. A same-scope aggregation bug in component classification was also fixed so D2 and D3 evidence rows are counted per phase.

## Fresh Evidence

- Fresh producer: Slurm job `59530203`, `htzhulab`, `COMPLETED`, exit `0:0`, elapsed `00:18:53`, log `logs/route_C/round03/R1Final_59530203_20260719_065904.log`.
- Superseded failed attempt: Slurm job `59530017`, `htzhulab`, `FAILED`, exit `2:0`, elapsed `00:19:02`, log `logs/route_C/round03/R1Final_59530017_20260719_063440.log`; zero-credit validator failure after fresh swap rows were generated but before component classification aggregation was repaired.
- Fresh aggregation command: `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/evaluation/route_C_round03/run_full_replay_and_interventions.py --aggregate-only --manifest results/route_C/round03/C0/phase_checkpoint_inventory.csv --anchor results/route_C/round03/C0/immutable_anchor.json --out results/route_C/round03/R1 --device cuda`.
- Fresh R1 accounting receipt: `results/route_C/round03/R1/r1_reviewer_revision_repair_accounting.json`.

R1 controls now report 264 rows total: 88 `positive_negative_prototype_swap` rows, all `pass=True` and `observed_behavior=KNOWN_BAD_DETECTED_HARMFUL`; 88 `no_op` rows and 88 `anchor_residual_control_off_path` rows remain zero-effect with no nonzero changed-logit/voxel rows.

## Validators

- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_C_round03/validate_r1_packet.py --strict results/route_C/round03/R1` passed.
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_C_round03/validate_r2_packet.py --strict results/route_C/round03/R2` passed.
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_C_round03/validate_final_packet.py --strict results/route_C` passed.
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python -m pytest tests/route_C_round03/test_r1_validator_known_bad.py tests/route_C_round03/test_r2_validator_known_bad.py` passed, including old terminal-looking bad packet and final-validator completion-only fail-open fixtures.

## Published Files

The local packet remains lightweight Markdown/CSV/JSON plus first-party source/tests. No checkpoints, NIfTI files, raw data, upload packages, or hosted-validation artifacts are published.

blocked_actions:
- validation packaging/upload remains blocked
- route promotion remains blocked
- M11 remains blocked
- cross-route merge remains blocked
- hosted metric claim remains blocked
- final scientific decision remains blocked

next_required_action: separate independent read-only reviewer re-reviews `results/route_C`
reason_if_no_route_promotion: awaiting independent review
