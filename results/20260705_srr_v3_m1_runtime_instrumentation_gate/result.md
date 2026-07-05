# SRR-v3 M1 Runtime Instrumentation Gate Result

## Status

`EXECUTED_UNAUDITED` with completion state `M1_NEEDS_EVIDENCE`.

## What Ran

I added `scripts/evaluation/export_srr_v3_m1_runtime_instrumentation.py` and ran it in eval-only mode on the existing bounded checkpoint for `srr_propref_shared_dual_dict`. The run used CPU and four explicit fold0 validation cases: `Case1002, Case2002, Case3004, Case3011`. No training, Slurm training, validation package, upload, route promotion, or M2 task was launched.

## Main Evidence

- Gate/residual export: `10` rows in `gate_residual_export.csv`. Aggregate edema gate mean is `0.014548602746799588`, and aggregate scar gate mean is `0.014547873986884952`. For both classes, open-rate at `0.05` and higher is `0.0`, while open-rate at `0.01` is `1.0`.
- Applied correction is small relative to bounded delta: aggregate edema correction abs mean `0.058121574111282825` with bounded delta abs mean `3.9955384731292725`; aggregate scar correction abs mean `0.05812669638544321` with bounded delta abs mean `3.9958872199058533`.
- Anchor alignment: `4` runtime rows in `anchor_context_alignment_export.csv`; all shape checks are `PASS`.
- No-T2 safety: Case1002 is LGE-only/no-T2 and reports `edema_logit_max=-20.0`, `final_edema_logit_max=-20.0`, `argmax_edema_voxels=0`, and `pathology_aware_edema_voxels=0`.
- Prototype coverage: `prototype_coverage_export.csv` reports `scar_positive=12`, `scar_negative=59`, `edema_positive=0`, `edema_negative=0`, and `t2_present_edema_positive=0`. This is the readiness blocker.

## Source-Line Evidence

- Baseline residual blend uses `final = anchor_logits + gate * bounded_delta` and exports gate/delta/residual at `src/care_myocardium/models/srr_propref.py:624-644`.
- No-T2 edema logits are clamped before final logits at `src/care_myocardium/models/srr_propref.py:934-937`; the baseline blend also clamps final class 4 logits for no-T2 at `src/care_myocardium/models/srr_propref.py:635-637`.
- Baseline preservation loss uses anchor confidence and gate penalty at `scripts/training/run_srr_propref_myops_fold0.py:436-471`.
- Runtime prototype bank loading occurs at `scripts/training/run_srr_propref_myops_fold0.py:1160-1178`.

## Conclusion

M1 instrumentation exists and produced real runtime CSV evidence. It does not prove formal training adequacy or SRR-v3 readiness. The existing bounded checkpoint remains diagnostic-only because the actual source summary has an empty edema prototype bank and only `6` optimizer steps.
