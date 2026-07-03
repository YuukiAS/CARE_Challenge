# Resource Audit

- safe cases source: `results/20260625_cine_geometry/safe_cases.csv`
- mismatch cases source: `results/20260625_cine_geometry/mismatch_cases.csv`
- adapter metrics source: `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv`
- output directory: `results/20260703_cine_temporal_resume`
- Python executable: `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`
- SimpleITK version: `2.5.3`
- optical-flow implementation: `skimage.registration.optical_flow_ilk`, CPU only.
- optical-flow max side before displacement estimation: `96` pixels; displacement is rescaled before full-resolution warp/sanity.
- GPU jobs: none.
- Network/downloads/uploads: none.
- External weights downloaded in this run: none.
- Total runtime seconds: `102.25`

Variant coverage:

- `cine_reference_control_recheck`: completed.
- `cine_deformable_or_feature_warp`: completed as first-party dense optical-flow/feature-warp proxy with folding/smoothness sanity; not claimed as validated registration.
- `cine_motion_descriptor_temporal_refiner`: completed as descriptor/temporal aggregation proxy; not claimed as registration.
- `cine_anatomy_prior_temporal_adapter`: local CineMA artifacts exist and are audited in `anatomy_prior_adapter_audit.md`; no new adapter run or external download was performed.
