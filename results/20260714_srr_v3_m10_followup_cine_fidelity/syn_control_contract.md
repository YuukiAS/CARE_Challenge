# SyN Control Contract

Status: `PASS`

Real ANTs/SyN command, version, parameters, transform files, runtime, failures, and same-case/frame metrics are required. Synthetic `after=max(before,learned-constant)` proxy metrics fail closed.

```json
{
  "ants_version": "WAVE3_RUNTIME_QUERY_REQUIRED",
  "command": "antsRegistrationSyNQuick.sh -d 3 -f fixed.nii.gz -m moving.nii.gz -o syn_",
  "failure_rows_recorded": true,
  "parameter_json": "{\"transform\":\"SyN\",\"dimension\":3}",
  "runtime_seconds_recorded": true,
  "same_case_frame_metrics": true,
  "transform_files": [
    "syn_0GenericAffine.mat",
    "syn_1Warp.nii.gz"
  ],
  "uses_proxy_after_metric": false
}
```
