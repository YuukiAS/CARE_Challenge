# Metrics Summary

status: `SYN_SMOKE_COMPLETED_NEEDS_SAFE_SUBSET_MATRIX`

This pass now includes one bounded ANTsPy SyN smoke row. It is stronger than the
previous translation/Demons-only or proxy-only evidence, but it is not a full
registration result because it covers one downsampled case and lacks a full
same-split matrix and deformation-field plausibility audit.

## SyN Smoke

| metric | value |
| --- | --- |
| case | `Case1001` |
| moving frame | `9` |
| runtime seconds | 5.705 |
| image NCC before | 0.948284 |
| image NCC after | 0.962654 |
| myocardium consistency before | 0.661256 |
| myocardium consistency after | 0.790390 |
| LV consistency before | 0.765556 |
| LV consistency after | 0.912357 |

## VoxelMorph Adapter Probe

This pass now also includes a bounded PyTorch VoxelMorph adapter probe. The
local `voxelmorph.nn.models.VxmPairwise` API runs on `Case1001` frame 9 -> frame
0 at `(16,64,64)`, but no cardiac pretrained weights are loaded. The resulting
field is near identity and is not a successful learned-registration result.

| metric | value |
| --- | --- |
| status | `VOXELMORPH_ADAPTER_PROBE_COMPLETE_NOT_TRAINED_NOT_FULL_REGISTRATION` |
| runtime seconds | 0.140364 |
| image NCC before -> after | 0.958767 -> 0.958769 |
| myocardium consistency before -> after | 0.669323 -> 0.669323 |
| LV consistency before -> after | 0.765756 -> 0.765756 |
| max displacement magnitude | 0.000047 |
| Jacobian min / max | 0.999951 / 1.000023 |
| folding proxy voxels | 0 |

Existing evidence available for context:

- CineMA adapter metrics:
  `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv`
- Existing translation preflight code:
  `scripts/evaluation/cinemyops_registration_preflight.py`
- Existing Demons fallback code:
  `scripts/evaluation/cine_temporal_motion_resume_20260704.py`
- Existing optical-flow/descriptor code:
  `scripts/evaluation/cine_motion_hardmode_20260703.py`

Current gate result:

| requirement | evidence | status |
| --- | --- | --- |
| CineMA attempt or blocker | Historical adapter evidence exists | `PARTIAL_SUPPORTED` |
| ANTs/SyN attempt | One bounded ANTsPy SyN smoke completed on `Case1001` | `SMOKE_SUPPORTED_NEEDS_SAFE_SUBSET` |
| VoxelMorph attempt | PyTorch `VxmPairwise` adapter probe completed, but untrained near-identity output has no registration value | `ADAPTER_PROBE_COMPLETE_NEEDS_TRAINED_OR_PUBLIC_WEIGHT_ROW` |
| TPS/B-spline/Demons fallback | Demons fallback script exists; not promoted | `FALLBACK_NOT_PROMOTED` |
| warp sanity | SyN transform files exist; Jacobian/folding audit not yet computed | `PARTIAL_MISSING_JACOBIAN` |
| downstream metric | no same-split matrix or hosted metric | `MISSING_RUNTIME_EVIDENCE` |

Conclusion: `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP`.
