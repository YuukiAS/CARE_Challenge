# CineMA Status

status: `PARTIAL_ANATOMY_PRIOR_ONLY`

The existing CineMA adapter evidence is useful but not sufficient for the full
SRR-v2.5 Cine branch.

Evidence found:

- `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/run_info.json`
- `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv`
- `results/cinema_adapter/external/CineMA/README.md`
- `results/cinema_adapter/external/CineMA/LICENSE`

The adapter label semantics in `run_info.json` are:

- `0`: background
- `1`: RV
- `2`: myocardium
- `3`: LV

CARE remapping used by prior scripts maps CineMA myocardium/LV anatomy into
compact anatomy proxies. This does not create a CineMyoPS pathology head. Class
3 scar/pathology behavior remains a negative control unless a downstream
pathology model is implemented and evaluated.

Registration status:

- frame0/reference-only: control only
- CineMA keyframes without registration: anatomy prior only
- SimpleITK translation/Demons/optical flow: fallback/proxy evidence
- ANTs/SyN: bounded ANTsPy SyN smoke completed on `Case1001` frame 9 -> frame 0; smoke only, not full same-split registration evidence
- VoxelMorph: bounded import succeeds, but the local source lacks the common `voxelmorph.networks`, `voxelmorph.torch`, and `voxelmorph.tf` adapter APIs

Conclusion: `PASS` is not supported. The allowed state is
`PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`.
