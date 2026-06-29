# Result 20260628 MyoPS Proposal

All three formal proposal variants completed on `htzhulab` without changing fold split, label mapping, evaluator, or hosted validation semantics.

## Formal Jobs

| variant | job_id | state | elapsed | stop reason | budget |
| --- | --- | --- | ---: | --- | --- |
| `proposal_pos_neg_basic` | `56912267` | `COMPLETED` | `06:31:10` | `max_runtime_seconds` | `OK` |
| `proposal_anatomy_distance` | `56912269` | `COMPLETED` | `06:33:09` | `max_runtime_seconds` | `OK` |
| `proposal_uncertainty_gate` | `56942380` | `COMPLETED` | `06:31:05` | `max_runtime_seconds` | `OK` |

Original uncertainty job `56912268` failed early because the checkpoint path was left as a zero-byte artifact; checkpoint saving was repaired and the formal route was rerun as `56942380`.

## Main Metrics

| variant | edema all Dice | edema GT+ Dice | edema no-T2 empty Dice | scar all Dice | scar LGE-only Dice |
| --- | ---: | ---: | ---: | ---: | ---: |
| `proposal_pos_neg_basic` | `0.1768` | `0.1737` | `0.1786` | `0.1017` | `0.0722` |
| `proposal_anatomy_distance` | `0.0635` | `0.1745` | `0.0000` | `0.0956` | `0.0783` |
| `proposal_uncertainty_gate` | `0.4376` | `0.2034` | `0.5714` | `0.0969` | `0.0813` |

## Decision

Selection: `REVISE_PROPOSAL_AND_REPEAT`.

The uncertainty gate is the best proposal-side signal, especially for edema all-case/no-T2 stability, but it is not strong enough to select a proposal route for formal refinement. Scar remains weak, GT-positive edema HD95 remains high, and component/remote-FP burden remains large.

## Continuation Evidence

The parallel continuation sprint produced useful repair directions:

- loss/decode calibration: `DECODE_CALIBRATION_SIGNAL`
- pathology checkpoint selection: `FINAL_BETTER_THAN_PATCH_BEST`
- hard-negative memory: `HARDNEG_PREFLIGHT_ONLY`
- soft-ROI geometry: `REFINE_WAITING_FOR_PROPOSAL_SELECTION`
- SRR-v2 core rebuild: `CORE_REBUILD_DEFER`

These should be integrated into a repeat proposal route rather than starting formal MyoPS refinement from the current checkpoints.

## All-Variant Decode Audit Note

A post-aggregation attempt to rerun decode/checkpoint audit across all three variants (`56949174`) failed after `00:57:06` with exit code `1:0` and no traceback beyond startup logging. The failed rerun is not used as evidence. The earlier valid `20260629_loss_decode_calibration` and `20260629_pathology_checkpoint_selection` outputs remain scoped to `proposal_pos_neg_basic`.
