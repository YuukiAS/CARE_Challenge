# Final Status 20260625 Fast Goal

status: `MYOPS_SRR_SELECTED`

## Subtasks

| subtask | result | decision |
| --- | --- | --- |
| `20260625_srr_recovery` | `results/20260625_srr_recovery/result.md` | `results/20260625_srr_recovery/decision.md`: `GO_RESCUE_ABLATION` |
| `20260625_srr_rescue_ablate` | `results/20260625_srr_rescue_ablate/result.md` | `results/20260625_srr_rescue_ablate/model_selection.md`: `SELECT_SRR_RECOVERED` |
| `20260625_cine_geometry` | `results/20260625_cine_geometry/result.md` | `results/20260625_cine_geometry/decision.md`: `GO_CINE_TEMPORAL_PREFLIGHT` |

## Selected MyoPS Route

- Selected route: `srr_expert_dropout` from Phase 1 recovery, recorded as `best_srr_recovered` in Phase 2.
- Fold0 edema GT-positive Dice: `0.1928`; HD95: `97.7248`.
- Fold0 scar all-case Dice: `0.0923`; HD95: `127.0317`.
- This beats the previous conditional anchor, late-fusion no-dictionary ablation, and weak-SIP retrieval ablation on the primary fold0 pathology Dice comparisons.
- Caveat: absolute pathology Dice remains low and false-positive/component burden remains high; this is a route selection, not a fold-expansion-ready model claim.

## Jobs

| job_id | variant | state | runtime | node | log |
| --- | --- | --- | --- | --- | --- |
| `56315544` | `srr_task_tempered` | `COMPLETED` | `05:50:32` | `g180702` | `logs/SRRTempF0_56315544_20260624_134107.log` |
| `56315545` | `srr_soft_entropy` | `COMPLETED` | `06:31:25` | `g1807htzh01` | `logs/SRRSoftF0_56315545_20260624_170956.log` |
| `56315547` | `srr_expert_dropout` | `COMPLETED` | `06:30:51` | `g1807htzh01` | `logs/SRRDropF0_56315547_20260624_172908.log` |
| `56469952` | `late_fusion_no_dictionary` | `COMPLETED` | `06:31:09` | `g1807htzh01` | `logs/SRRLateF0_56469952_20260625_001729.log` |
| `56469990` | `retrieval_no_sip_or_weak_sip` | `COMPLETED` | `06:31:31` | `g1807htzh01` | `logs/SRRWeakF0_56469990_20260625_064840.log` |

## Cine Geometry

- Safe cases: `59`.
- Mismatch cases: `5`: `center_alpha_Case1009`, `center_alpha_Case1018`, `center_alpha_Case1020`, `center_alpha_Case1024`, `center_beta_Case2023`.
- Geometry decision: `GO_CINE_TEMPORAL_PREFLIGHT`.
- Reference-frame safe-subset preflight: class_1 myocardium Dice mean `0.5626`, class_2 LV Dice mean `0.7709`.
- Scar sanity remains failed/zero because the reused frozen CineMA anatomy prior has no scar head.

## Not Executed

- No validation submission, upload package, external data, networking, folds1-4 expansion, or 5-fold expansion was performed.
- Cine temporal training/preflight beyond the safe-subset reference control remains a follow-up task.
