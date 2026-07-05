# MANIFEST: 20260704_cine_full_cinema_registration

task_source: `prompts/tasks/20260704_cine_full_cinema_registration.md`

## Artifacts

- `result.md` - diagnostic result and gate decision.
- `asset_registry.md` - local CineMA, ANTsPy, SimpleITK, VoxelMorph, and proxy asset status.
- `cinema_status.md` - CineMA anatomy-prior status and limitation.
- `registration_option_matrix.md` - required strong registration matrix and current evidence state.
- `warp_sanity.csv` - method-level warp sanity evidence state, including the bounded SyN smoke row.
- `syn_probe_summary.json` - bounded ANTsPy SyN smoke metadata and transform paths.
- `syn_voxelmorph_probe.csv` - one-case SyN anatomy consistency measurements.
- `voxelmorph_adapter_probe.csv` - one-case PyTorch VoxelMorph adapter metrics; untrained near-identity probe only.
- `voxelmorph_adapter_probe_summary.json` - VoxelMorph adapter runtime and displacement summary.
- `strong_registration_probe/Case1001_syn_1Warp.nii.gz` - SyN forward warp evidence file.
- `strong_registration_probe/Case1001_syn_1InverseWarp.nii.gz` - SyN inverse warp evidence file.
- `strong_registration_probe/Case1001_syn_0GenericAffine.mat` - SyN affine transform evidence file.
- `metrics_summary.md` - metric gate summary with smoke-level caveats.
- `resource_log.md` - commands and local availability evidence.

## Current State

state: `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`

No validation package, external upload, git commit, git push, or training run was
performed. A bounded ANTsPy SyN smoke probe and an untrained PyTorch VoxelMorph
adapter probe were performed; full same-split Cine registration evidence remains
incomplete.
