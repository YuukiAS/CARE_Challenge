# Result 20260704 MyoPS Anchor SRR Fold0 Formal

experiment_adequacy_decision: PASS
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNRESOLVED
self_assessed_status: EXECUTED_UNAUDITED
role: executor
review_required: true

## Execution Summary

Verified the LOCKED contract and Phase 1-5 PASS_PREFLIGHT prerequisites. Ran bounded pre-submit Stage 0 sanity for all three required aliases, then used the CARE htzhulab GPU policy for the formal fold0 Slurm array.

No validation package, external upload, network access, fold expansion, git commit, or git push was performed.

## Variant Mapping

| formal_variant | script_alias | pre_submit_stage0 | formal_stage0 | formal_summary | adequacy |
| --- | --- | --- | --- | --- | --- |
| `anchored_srr_v25_full` | `srr_propref_shared_dual_dict` | `PASS` | `PASS` | `present` | `PASS` |
| `anchored_scar_precision_edema_safe` | `srr_propref_scar_precision` | `PASS` | `PASS` | `present` | `PASS` |
| `anchored_conservative_cascade_no_proto_or_frozen_proto` | `srr_propref_no_proto_cascade` | `PASS` | `PASS` | `present` | `PASS` |

## Job

- job_id: `57782211`
- log_path_glob: `logs/MyoPSAnchorSRRF0_*_57782211_*.log`
- formal_status: `COMPLETE`

Per-variant log files:
- `anchored_srr_v25_full` / `srr_propref_shared_dual_dict`: `/users/a/e/aereinh/CARE/logs/MyoPSAnchorSRRF0_0_57782213_20260704_022627.log`
- `anchored_scar_precision_edema_safe` / `srr_propref_scar_precision`: `/users/a/e/aereinh/CARE/logs/MyoPSAnchorSRRF0_1_57782214_20260704_022627.log`
- `anchored_conservative_cascade_no_proto_or_frozen_proto` / `srr_propref_no_proto_cascade`: `/users/a/e/aereinh/CARE/logs/MyoPSAnchorSRRF0_2_57782211_20260704_022627.log`

## Commands Run

- `evidence not recorded`

## Outputs

- Required result artifacts were written under `results/20260704_myops_anchor_srr_fold0_formal/`.
- Per-variant formal evidence is under `variants/<script_alias>/`: checkpoints, prediction exports, logs, summaries, and metric CSVs.

## Boundary

This executor does not authorize route promotion, route-negative stop, validation packaging/upload, fold expansion, commit, or push. Separate read-only audit remains required.
