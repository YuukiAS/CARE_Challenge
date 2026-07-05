# Hard Subgroup Review

The bounded hard-subgroup matrix and overlay packet remain important context.

Evidence reviewed:

- `results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/`
- `results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay/`
- `results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay/bounded_matrix_overlay_summary.md`

Findings:

- bounded matrix rows covered identity controls, three PropRef variants, and
  three isolated ablations;
- overlay/taxonomy packet contains 42 overlays and 96 taxonomy rows;
- no-anchor failures concentrate in remote-island/large false-positive patterns;
- anchor-enabled rows mainly show neutral or boundary-level changes;
- hard subgroup evidence explains why no-anchor is unsafe, but does not show a
  robust improvement path over nnU-Net.
