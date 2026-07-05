# Result 20260704 Cine Full CineMA Registration

status: `EXECUTED_UNAUDITED`
self_assessed_status: `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`
domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`

## Summary

This pass still does not complete the Cine registration task, but it no longer
stops at simple registration. A bounded ANTsPy SyN smoke probe was run on the
safe Cine case `Case1001` frame 9 to
frame 0. The probe completed in 5.705 seconds on a
shrunk 3D volume (`zyx=[14, 128, 128]`), improved
image NCC from 0.9483 to 0.9627,
and improved CineMA anatomy-label consistency to the reference prediction for
myocardium and LV.

This is useful evidence that the prior simple-registration-only boundary was too
weak. It is not enough to claim full Cine registration: it is one downsampled
case, lacks a safe-subset matrix, lacks Jacobian/folding audit for the SyN field,
and has no downstream hosted `myocardium_cinemyops` evidence.

This follow-up also ran a bounded PyTorch VoxelMorph adapter probe on the same
`Case1001` frame 9 -> frame 0 pair. The adapter now runs, but no cardiac
pretrained weights are loaded and the result is near identity: image NCC
`0.958767 -> 0.958769`, myocardium consistency `0.669323 -> 0.669323`, LV
consistency `0.765756 -> 0.765756`, and max displacement magnitude `0.000047`.
This closes the narrow "adapter not attempted" gap but does not provide a
successful learned-registration row.

## What Was Checked

- Existing CineMA adapter evidence exists under
  `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`.
- `ants` imports from the active Python environment as ANTsPy `0.6.3`.
- `antsRegistration` and `antsApplyTransforms` CLI binaries are not on `PATH`,
  so the runnable route is ANTsPy rather than ANTs CLI.
- `SimpleITK` imports as version `2.5.0`; translation/Demons remain fallback or
  control rows, not full registration evidence.
- `voxelmorph` now imports in a bounded probe from the local external source,
  and a PyTorch `voxelmorph.nn.models.VxmPairwise` one-case adapter probe now
  runs. It is untrained and near identity, so it remains diagnostic-only.

## SyN Smoke Evidence

| field | value |
| --- | --- |
| case | `Case1001` / `center_alpha` |
| fixed -> moving | frame 0 <- frame 9 |
| transform | `SyNOnly` via ANTsPy |
| image grid | downsampled x/y by 2, shape zyx `[14, 128, 128]` |
| runtime seconds | 5.705 |
| image NCC before | 0.948284 |
| image NCC after | 0.962654 |
| myocardium consistency before -> after | 0.661256 -> 0.790390 |
| LV consistency before -> after | 0.765556 -> 0.912357 |
| transform files | `results/20260704_cine_full_cinema_registration/strong_registration_probe/Case1001_syn_1Warp.nii.gz; results/20260704_cine_full_cinema_registration/strong_registration_probe/Case1001_syn_0GenericAffine.mat` |

## Key Decision

decision: `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`

The next Cine registration action is not more translation. It should run a
same-safe-subset comparison with:

- ANTsPy SyN on the same cases used by frame0/translation/Demons controls;
- VoxelMorph or equivalent learning-based adapter with trained/public weights,
  or a precise domain/weight blocker if only untrained PyTorch adapter evidence
  is available;
- Jacobian/folding or equivalent warp plausibility for each deformation field;
- myocardium/LV consistency and downstream proxy metrics on the same rows.

No training, validation packaging, external upload, git commit, or git push was
performed in this pass.

## Verification Commands

```bash
timeout 600 ./envs/env_CARE/bin/python <bounded ANTsPy SyN probe>
```

Result: `SYN_SMOKE_COMPLETED`, `Case1001`, runtime `5.705` seconds.

```bash
timeout 45 ./envs/env_CARE/bin/python -c "import voxelmorph as vxm; print(vxm.__file__)"
```

Result: import succeeds from
`results/20260704_external_assets_cinema_registration/external_assets/voxelmorph/voxelmorph/__init__.py`.

```bash
timeout 60 ./envs/env_CARE/bin/python -c "import voxelmorph as vxm; print(hasattr(vxm, 'networks'))"
```

Result: `False`; `voxelmorph.networks`, `voxelmorph.torch`, and `voxelmorph.tf`
are not available from this local source. Trained/public-weight learned
registration work remains.

```bash
MPLCONFIGDIR=/users/a/e/aereinh/.tmp/codex-care/matplotlib \
  ./envs/env_CARE/bin/python scripts/evaluation/cine_voxelmorph_adapter_probe.py --device cpu
```

Result: exit `0`; `voxelmorph.nn.models.VxmPairwise` adapter completed on
`Case1001`, frame 9 -> frame 0, but with untrained near-identity behavior. This
is not full learned-registration evidence.

## Artifacts

- `asset_registry.md`
- `cinema_status.md`
- `registration_option_matrix.md`
- `warp_sanity.csv`
- `syn_probe_summary.json`
- `syn_voxelmorph_probe.csv`
- `voxelmorph_adapter_probe.csv`
- `voxelmorph_adapter_probe_summary.json`
- `strong_registration_probe/Case1001_syn_1Warp.nii.gz`
- `strong_registration_probe/Case1001_syn_1InverseWarp.nii.gz`
- `strong_registration_probe/Case1001_syn_0GenericAffine.mat`
- `metrics_summary.md`
- `resource_log.md`
- `MANIFEST.md`
