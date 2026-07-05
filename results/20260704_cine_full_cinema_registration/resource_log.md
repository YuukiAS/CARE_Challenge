# Resource Log

status: `DIAGNOSTIC_ONLY`

Commands run in this pass:

```bash
rg -n "CineMA|cinema|ANTs|antspy|antsRegistration|SyN|VoxelMorph|voxelmorph|TPS|thin plate|SimpleITK|optical flow|registration" src scripts jobs prompts results -g '!results/**/runtime_smoke*/**' -g '!results/**/checkpoints/**'
```

Result: located existing CineMA adapter, SimpleITK translation preflight,
SimpleITK Demons fallback, optical-flow/descriptor proxy, MyoPS alignment audit,
and task files requiring SyN/VoxelMorph.

```bash
./envs/env_CARE/bin/python -c "import importlib.util; mods=['ants','antspyx','SimpleITK','voxelmorph','vxm','torch','monai']; print('\n'.join(f'{m}: {bool(importlib.util.find_spec(m))}' for m in mods))"
```

Result:

```text
ants: True
antspyx: False
SimpleITK: True
voxelmorph: True
vxm: False
torch: True
monai: True
```

```bash
which antsRegistration
which antsApplyTransforms
```

Result: both commands exited `1`; binaries are not on `PATH`.

```bash
./envs/env_CARE/bin/python -c "import ants, SimpleITK as sitk; print('ants_module', ants.__file__); print('ants_version', getattr(ants, '__version__', 'unknown')); print('sitk_version', sitk.Version_VersionString())"
```

Result:

```text
ants_module /users/a/e/aereinh/CARE/envs/env_CARE/lib/python3.12/site-packages/ants/__init__.py
ants_version 0.6.3
sitk_version 2.5.0
```

```bash
./envs/env_CARE/bin/python -c "import importlib.util; spec=importlib.util.find_spec('voxelmorph'); print('voxelmorph_spec_found', bool(spec)); print('voxelmorph_origin', spec.origin if spec else 'missing')"
```

Result:

```text
voxelmorph_spec_found True
voxelmorph_origin /users/a/e/aereinh/CARE/results/20260704_external_assets_cinema_registration/external_assets/voxelmorph/voxelmorph/__init__.py
```

Direct `import voxelmorph` did not complete within the interactive wait and was
interrupted with `KeyboardInterrupt` while importing its dependency chain. This
is recorded as `SOURCE_PRESENT_IMPORT_BLOCKED`.

## 2026-07-04 Strong Registration Follow-up

Reason: user correctly challenged that translation/Demons/proxy evidence cannot substitute for SyN/VoxelMorph-level registration.

Commands executed:

```bash
timeout 45 ./envs/env_CARE/bin/python - <<'PY'
import voxelmorph as vxm
print(vxm.__file__)
PY
```

Result: bounded import succeeded from `results/20260704_external_assets_cinema_registration/external_assets/voxelmorph/voxelmorph/__init__.py`.

```bash
timeout 60 ./envs/env_CARE/bin/python - <<'PY'
import voxelmorph as vxm
print(hasattr(vxm, 'networks'))
PY
```

Result: `False`; `voxelmorph.networks`, `voxelmorph.torch`, and `voxelmorph.tf` are unavailable from this local source. Adapter remains unresolved.

```bash
MPLCONFIGDIR=/users/a/e/aereinh/.tmp/codex-care/matplotlib \
  ./envs/env_CARE/bin/python scripts/evaluation/cine_voxelmorph_adapter_probe.py --device cpu
```

Result: exit `0`. The PyTorch `voxelmorph.nn.models.VxmPairwise` adapter ran on
`Case1001`, frame 9 -> frame 0, with output
`voxelmorph_adapter_probe.csv`. The probe is explicitly untrained and near
identity: NCC `0.958767 -> 0.958769`, myocardium Dice `0.669323 -> 0.669323`,
LV Dice `0.765756 -> 0.765756`, max displacement magnitude `0.000047`, and
folding proxy voxels `0`.

```bash
timeout 600 ./envs/env_CARE/bin/python <bounded ANTsPy SyN probe>
```

Result: `SYN_SMOKE_COMPLETED` on `Case1001`, frame 9 -> frame 0. Runtime 5.705 seconds; NCC 0.948284 -> 0.962654; myocardium consistency 0.661256 -> 0.790390; LV consistency 0.765556 -> 0.912357.

New artifacts:

- `syn_probe_summary.json`
- `syn_voxelmorph_probe.csv`
- `voxelmorph_adapter_probe.csv`
- `voxelmorph_adapter_probe_summary.json`
- `strong_registration_probe/Case1001_syn_1Warp.nii.gz`
- `strong_registration_probe/Case1001_syn_1InverseWarp.nii.gz`
- `strong_registration_probe/Case1001_syn_0GenericAffine.mat`
