# Ablation Review

The full fold0 matrix has the required diagnostic rows:

- `srr_propref_shared_dual_dict`
- `srr_propref_no_proto_cascade`
- `srr_propref_scar_precision`
- `srr_v25_no_local_refine`
- `srr_v25_no_anatomy_roi`
- `srr_v25_no_anchor`

Interpretation:

- Removing the anchor is catastrophic on both scar and edema, so SRR must remain
  baseline-preserving.
- Removing local refinement is almost identity-like, so current crop refinement
  is not delivering measurable full-fold0 gain.
- Removing anatomy ROI is near-neutral, so current anatomy-distance soft gates
  are implemented but not yet visibly useful.
- No-proto gives a tiny edema improvement but scar loss and one edema remote-FP
  regression; this is not a route win.

The matrix is diagnostic because the source checkpoints are bounded 6-step
mechanism probes.
