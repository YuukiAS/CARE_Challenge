# Claim Table

| claim | audit finding | evidence | decision |
| --- | --- | --- | --- |
| visual SRR-v2/v2.5 contract carried forward | Supported | `results/20260704_srr_v25_visual_contract_lock/result.md` | `SUPPORTED` |
| anti-laziness acceptance tests | Partially supported with legacy external findings | latest validator exits 0 but reports 10 older `CLAIM_WITHOUT_RUNTIME_EVIDENCE` issues outside this packet | `SUPPORTED_WITH_LEGACY_CAVEAT` |
| baseline-preserving nnU-Net residual/gated correction | Supported | `BaselinePreservingResidualGate` blends `anchor_logits + gate * bounded_delta`; no-anchor full-fold0 row is harmful | `SUPPORTED` |
| real train/OOF prototype banks loaded at runtime | Supported | runner calls `build_prototype_bank_from_labeled_features`, writes `prototype_bank_summary.json`, and model exposes runtime bank behavior | `SUPPORTED` |
| semantic dictionary/retrieval slots ablated | Supported diagnostically | bounded matrix includes no-proto, scar-precision, shared-dual-dict rows | `DIAGNOSTIC_SUPPORTED` |
| pathology-specific proposal/refinement | Supported | separate scar/edema proposal logits, soft ROI, crop refinement, and decode paths | `SUPPORTED` |
| anatomy distance/soft gate ROI behavior | Supported | `P_union/P_LV/P_RV`, distance, uncertainty, and soft gate tensors are emitted and ablated by no-anatomy row | `SUPPORTED` |
| no-T2 edema safety | Supported | loss, anchor input, inference logits, decode/export toy validator, and sanity rows block no-T2 edema | `SUPPORTED` |
| same-split metrics beat nnU-Net | Not supported | full fold0 rows are near-identity except no-anchor is strongly harmful | `NOT_SUPPORTED` |
| hard subgroup spatial failures explained | Supported diagnostically | bounded overlay/taxonomy packet has 42 overlays and 96 taxonomy rows | `DIAGNOSTIC_SUPPORTED` |
| Cine full registration complete | Not supported | ANTsPy SyN smoke and untrained VoxelMorph adapter probe exist, but no same-safe-subset matrix | `REGISTRATION_GAP_REMAINS` |
