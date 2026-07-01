# Cascade Teacher Failure Interpretation

Formal status: `STOP_NO_CASCADE_SIGNAL`

## What Failed

The cascade teacher route did not fail because of missing teacher artifacts,
missing exports, or an evaluator/runtime error. Those parts now work:

- OOF-5 teacher cache coverage is complete.
- All three formal variants completed.
- Each formal variant exported `44/44` validation predictions.
- The route finalizer produced metrics, selection, subgroup metrics,
  component/HD tables, and teacher-student deltas.

The failure is model/decision evidence: the refiner did not produce a material
improvement over the nnU-Net teacher/reference baseline.

## Evidence

| variant | eval decision | edema Dice delta on T2+ | scar Dice delta | interpretation |
| --- | --- | ---: | ---: | --- |
| `nnunet_anatomy_prior_refiner` | `fail_stop_refiner_candidate` | 0.0014 | 0.0000 | Too close to teacher; no pathology rescue. |
| `nnunet_pathology_teacher_srr_refiner` | `fail_stop_refiner_candidate` | 0.0006 | 0.0000 | Too close to teacher; no meaningful scar signal. |
| `coarse_to_fine_srr_roi` | `fail_stop_refiner_candidate` | 0.0019 | 0.0028 | Smallest positive scar/edema movement, still too small for selection and not robust against component burden risk. |

## Mechanism Assessment

The current cascade design is too conservative to rescue the weak SRR signal in
a leaderboard-relevant way. It mostly preserves the teacher output. The few
edits it makes are tiny, and the available component/HD evidence does not show
a clean reduction in false positives or a durable scar/edema gain.

This rules out "missing teacher cache" and "evaluation plumbing" as the main
blockers for this route. The remaining plausible blockers are residual
calibration, component control, thresholding, or insufficient pathology-specific
training signal.

## Next Action

Do not select this route from the formal variants. Continue improvement only as
isolated follow-up experiments.

The submitted component-guard revision `57274444_[0-1]` tests the next narrow
hypothesis: stricter residual magnitude and higher pathology thresholds may
reduce component/remote false positives while keeping any small positive
pathology movement.

No fold expansion or validation upload is justified from the formal cascade
evidence alone.
