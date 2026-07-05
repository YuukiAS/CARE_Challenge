
# Cine Branch Status Audit

Audit basis commit: `3f30e0ee4b8c951f700fe50de8810bac8e196c23`.

Checked local result path: `results/20260704_cine_full_cinema_registration/`.

Evidence found:

- CineMA adapter context exists historically, but no full temporal dictionary integration result is present in this task packet.
- ANTsPy SyN smoke exists for `Case1001` frame 9 -> frame 0: image NCC `0.948284 -> 0.962654`, myocardium consistency `0.661256 -> 0.790390`, LV consistency `0.765556 -> 0.912357`.
- VoxelMorph PyTorch adapter probe exists but is untrained and near identity: image NCC `0.958767 -> 0.958769`, myocardium consistency unchanged, LV consistency unchanged, max displacement magnitude `0.000047`.
- SimpleITK translation/Demons and optical flow remain fallback/proxy routes, not promoted full registration evidence.
- `results/20260704_cine_temporal_dictionary_integration/` is absent locally (`EVIDENCE_NOT_FOUND`).

Status: `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP` remains accurate. Missing for full Cine evidence: same-safe-subset registration matrix, temporal dictionary, frame-quality router, temporal aggregation metrics, and downstream same-subset metrics.
