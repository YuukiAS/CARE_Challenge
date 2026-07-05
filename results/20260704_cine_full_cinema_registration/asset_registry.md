# Asset Registry

status: `DIAGNOSTIC_ONLY`

| asset | local evidence | status | notes |
| --- | --- | --- | --- |
| CineMA adapter outputs | `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/run_info.json`, `metrics.csv` | `EXISTS_HISTORICAL_ADAPTER` | Historical run info records up to 64 train and 15 validation cases, frame strategy `ed_middle_representative`, ACDC-trained CineMA anatomy labels. The JSON stores older `/overflow` paths, but the active `/users` result files are readable. |
| CineMA source copy | `results/cinema_adapter/external/CineMA/README.md`, `LICENSE` and `results/20260704_external_assets_cinema_registration/external_assets/CineMA/` | `SOURCE_PRESENT` | Anatomy prior only; no CARE scar/pathology head. |
| ANTsPy | Python module `ants` under `envs/env_CARE/lib/python3.12/site-packages/ants`, version `0.6.3`; `syn_probe_summary.json` | `SYN_SMOKE_COMPLETED` | Prefer ANTsPy SyN because ANTs CLI is absent from `PATH`. One bounded downsampled smoke completed. |
| ANTs CLI | `antsRegistration`, `antsApplyTransforms` | `NOT_ON_PATH` | CLI route blocked unless module/path setup is fixed. |
| SimpleITK | Python import version `2.5.0` | `AVAILABLE_FALLBACK` | Supports translation/Demons/B-spline style probes, but this is not a substitute for SyN/VoxelMorph. |
| VoxelMorph source | `results/20260704_external_assets_cinema_registration/external_assets/voxelmorph/`; `voxelmorph_adapter_probe.csv` | `PYTORCH_ADAPTER_PROBE_COMPLETE_UNTRAINED` | Local PyTorch `voxelmorph.nn.models.VxmPairwise` adapter runs on `Case1001` frame 9 -> frame 0 at `(16,64,64)`, but no cardiac pretrained weights are loaded. Output is near identity, so this is adapter evidence only, not full registration evidence. |
| Existing optical-flow proxy | `scripts/evaluation/cine_motion_hardmode_20260703.py` | `PROXY_ONLY` | Useful diagnostic, not validated registration completion. |
| Existing SimpleITK translation preflight | `scripts/evaluation/cinemyops_registration_preflight.py` | `LOWER_BASELINE_ONLY` | Translation-only registration must not be reported as full registration. |
| Existing SimpleITK Demons fallback | `scripts/evaluation/cine_temporal_motion_resume_20260704.py` | `FALLBACK_ONLY` | Has Jacobian/folding sanity code; still needs same-split comparison against SyN/VoxelMorph. |
