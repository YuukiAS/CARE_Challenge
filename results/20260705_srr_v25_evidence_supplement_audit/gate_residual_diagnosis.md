
# Gate / Residual Diagnosis

Audit basis commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

## Source Evidence

Code paths found:

- `src/care_myocardium/models/srr_propref.py:571`
- `src/care_myocardium/models/srr_propref.py:633`
- `src/care_myocardium/models/srr_propref.py:938`
- `src/care_myocardium/models/srr_propref.py:943`
- `scripts/training/run_srr_propref_myops_fold0.py:428`
- `scripts/training/run_srr_propref_myops_fold0.py:1523`
- `scripts/training/run_srr_propref_myops_fold0.py:681`

Runtime logging path: `scripts/training/run_srr_propref_myops_fold0.py` records `baseline_gate_mean` and `baseline_residual_abs_mean` in bounded training logs. The available bounded matrix logs show anchor-enabled gate means around `0.017986` and residual magnitudes around `0.065-0.096` depending on row. Full-fold0 eval CSVs contain ROI `residual_abs_mean` proxies, but no full-fold0 gate open-rate or `bounded_delta` distribution.

## Diagnosis

Anchor-enabled full-fold0 rows are near identity versus nnU-Net. The best supported explanation is: closed-biased baseline gate plus small bounded residuals kept outputs close to the nnU-Net anchor. However, the exact causal split among gate too small, bounded_delta too small, decode fallback, and training underfit cannot be fully resolved because full-fold0 runtime gate open-rate and bounded_delta distributions were not exported.

Evidence status: `PARTIAL_RUNTIME_EVIDENCE`. Required lightweight follow-up, if needed, is an eval-only instrumentation pass that exports per-case/class `baseline_residual_gate` mean/p95/open-rate, `bounded_delta_srr` abs mean/p95, `gate*bounded_delta` abs mean, and decode-mode final label deltas against nnU-Net. This does not require training.
