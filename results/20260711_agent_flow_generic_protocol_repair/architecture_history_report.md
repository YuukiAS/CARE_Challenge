# Architecture And History Report

- `wiki/current_state.yaml` was added as the current review source.
- History generator now supports discovered `wiki/history/M*/` versions and
  dynamic predecessor delta.
- M8/M9 special narrative is stored as history annotations, not generic code
  conditionals.
- `reconcile_review_status.py` now uses `--milestone-id` and updates
  `wiki/current_state.yaml` deterministically.
