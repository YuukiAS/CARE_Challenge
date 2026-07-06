# CineMA/Cine Usage Report

status: `CINE_SECONDARY_DIAGNOSTIC_STARTED`
cine_decision: `CINE_REGISTRATION_GAP_REMAINS`
temporal_dictionary_status: `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`

## Source And Scope

- M5 review gate: `/users/a/e/aereinh/CARE/results/20260705_srr_v3_m5_cine_secondary_contract/review.md` contains `M5_AUDITED_DIAGNOSTIC_GO`.
- CineMA adapter metrics: `/users/a/e/aereinh/CARE/results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics_summary.json`.
- CineMA frame metrics: `/users/a/e/aereinh/CARE/results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv`.
- Source status: existing frozen CineMA anatomy-prior adapter evidence from M5; M7 did not train CineMA and did not package or upload validation outputs.
- Class mapping: CineMA anatomy output is treated as anatomy-only evidence. In prior CARE preflight notes, CineMA label `2` maps to compact myocardium `1`, CineMA label `3` maps to compact LV `2`; it has no scar/pathology head.
- Input preprocessing/output shape: inherited from the existing adapter artifacts; this M7 step did not rerun the adapter, so per-file tensor shape is not newly asserted here.

## What M7 Started

- Wrote `registration_same_subset_matrix.csv` from the M5 audited evidence matrix into the M7 packet.
- Wrote `cine_metrics_summary.csv` with anatomy-prior metrics and hosted-metric caveats.
- Wrote `temporal_dictionary_evidence.csv` with an explicit registration-gated temporal dictionary status.

## Decision

Frame0/ED identity control, one-case SyN smoke, untrained VoxelMorph, SimpleITK/Demons fallback with Jacobian concerns, and optical-flow descriptor/proxy evidence are not sufficient to claim completed Cine registration. Because no qualified non-reference registration option is present, M7 marks temporal dictionary construction as blocked by the registration gap rather than substituting frame0-only or descriptor-only evidence.
