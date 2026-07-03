# Label Export QC

scope: local diagnostic only

- evaluator: local safe-case proxy from `scripts/evaluation/cine_motion_hardmode_20260703.py`.
- raw ground-truth labels: `200 -> compact 1 myocardium`, `500 -> compact 2 LV`, `2221 -> compact 3 scar_sanity`.
- CineMA anatomy-prior prediction remap: `2 -> compact 1 myocardium`, `3 -> compact 2 LV`; no scar/pathology prediction head exists.
- observed compact GT labels in scored case metrics: `[1, 2, 3]`.
- observed compact predicted labels with nonzero volume: `[1, 2]`.
- validation export: `not performed`.
- upload-ready package: `not performed`.
- raw-label submission decode path: `evidence not found` because validation packaging/upload were forbidden.
- hosted `myocardium_cinemyops`: `evidence not found`.

Conclusion: compact-label local proxy scoring is internally consistent for the safe subset, but this is not challenge-facing raw-label export QC.
