---
task_key: 20260805_care_myops_single_slice_hotfix_provenance_addendum
task_kind: audit
task_type: submission_runtime_hotfix_provenance
status: AUTHORIZED_BY_USER
branch_policy: main-only
precedence: overrides_conflicting_provenance_fields_in_20260805_care_myops_single_slice_hotfix_repackage_controller
architecture_impact: none
model_change_authorized: false
training_authorized: false
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_prediction_upload_authorized: false
---

# MyoPS single-slice hotfix: model-invariance and organizer provenance addendum

This file must be read together with:

`prompts/tasks/20260805_care_myops_single_slice_hotfix_repackage_controller.md`

The purpose is to make the corrected organizer image auditable as a runtime-only derivative of the exact failed submission, not a new scientific model.

## 1. Exact base artifact

The only authorized base is:

```text
archive: MyoPS-OrganAgent.tar.gz
archive size: 4741640359
archive SHA256: 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b
loaded image ID: sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911
model contract commit: 55b95d45554590690c178578ef41712d23aa51c6
```

The corrected image must be built with `FROM care-myocardium-myops:attempt2-base`. It must not be rebuilt from the mutable repository MyoPS context and must not use CARE-ASE attempt3 files.

## 2. Required before/after invariance manifests

Create machine-readable manifests from both the base and corrected images. At minimum compare:

- `docker image inspect` OS, architecture, Entrypoint, Cmd, Env and WorkingDir;
- rootfs `diff_ids`, proving every base diff ID is an exact prefix of the corrected image diff IDs;
- five `checkpoint_best.pth` paths, sizes and SHA256 values;
- `plans.json` and `dataset.json` paths, sizes and SHA256 values;
- `/app/predict.py`, `/app/entrypoint.sh`, `/app/requirements.lock` SHA256 values;
- exact `pip freeze --all` output;
- nnU-Net, Python, PyTorch, NumPy, SciPy, SimpleITK and nibabel versions;
- absence of `/app/models/self_model`, CARE-ASE checkpoints, MoSAIC weights or other overlay assets.

Write:

```text
base_image_critical_manifest.json
corrected_image_critical_manifest.json
model_invariance_comparison.json
```

Hard requirements:

```text
model_checkpoint_hashes_equal=true
plans_dataset_hashes_equal=true
predict_entrypoint_requirements_hashes_equal=true
pip_freeze_equal=true
entrypoint_cmd_env_equal=true
base_rootfs_diff_ids_are_exact_prefix=true
forbidden_model_assets_present=false
```

Any false value stops the task with:

`MODEL_INVARIANCE_PROOF_FAILED`

## 3. Restrict changed filesystem paths

Inspect the appended corrected-image layers or equivalent exported filesystem delta. The only permitted effective changes are:

- the installed nnU-Net source file containing `compute_new_shape`;
- `/app/hotfix/single_slice_hotfix_receipt.json`;
- build-time temporary patch script path and its whiteout/removal metadata;
- OCI description/provenance labels.

No file under `/app/models`, `/app/predict.py`, `/app/entrypoint.sh`, `/app/requirements.lock`, or another installed package may change.

Write:

`corrected_image_filesystem_delta.json`

with exact changed paths and old/new SHA256 where applicable.

## 4. Functional proof that the scientific model did not change

Run the base and corrected images on the same 15 normal public MyoPS cases. Require for every case:

- both exit code 0;
- identical output case set;
- voxel arrays exactly equal;
- shape, spacing, origin and direction exactly equal;
- label sets exactly equal;
- canonical array+geometry SHA exactly equal.

Write:

```text
normal_case_exact_regression_casewise.csv
normal_case_exact_regression_summary.json
```

Required summary fields:

```text
case_count=15
array_exact_count=15
geometry_exact_count=15
canonical_sha_exact_count=15
status=PASS
```

This is the strongest practical proof that the runtime patch leaves ordinary model predictions unchanged.

## 5. Boundary proof

The corrected image must additionally pass:

- direct `compute_new_shape` singleton-axis permutation tests;
- depth-1 and depth-2 multi-spacing synthetic cases;
- a mixed batch containing all 15 normal cases plus all synthetic boundary cases;
- repeated deterministic runs;
- clean archive save/load followed by rerun;
- output geometry restored to each synthetic input geometry;
- no missing case after one pathological input.

The old image must reproduce at least one faithful zero-dimension failure before the patch is accepted.

## 6. Final provenance receipt

Create:

`corrected_myops_runtime_only_hotfix_provenance.json`

It must bind:

- old archive SHA and image ID;
- new archive SHA, size and image ID;
- old and new rootfs diff IDs;
- exact checkpoint/plans/dataset hashes;
- exact normal-case regression summary;
- exact patched source old/new SHA;
- patch function diff;
- boundary and mixed-batch test results;
- Git commit containing the hotfix context and validators;
- `model_changed=false`;
- `training_performed=false`;
- `checkpoint_selection_changed=false`;
- `inference_configuration_changed=false`;
- `only_runtime_preprocessing_fix=true`.

## 7. Independent server-side final audit

After the workstation returns the corrected archive and lightweight packet, the server must not run Docker. It must independently audit:

- corrected archive size/SHA against the workstation receipt;
- packet manifest and provenance receipt;
- exact five checkpoint hashes against the original frozen contract;
- normal 15-case exact-regression summary;
- boundary/mixed-batch/clean-load validator status;
- new public Drive link binding to the corrected archive;
- unsent organizer reply draft.

The server may return ready only with:

`CORRECTED_MYOPS_RUNTIME_ONLY_HOTFIX_READY_FOR_ORGANIZER_REEVALUATION`

## 8. Organizer-facing wording

The unsent reply draft should include one concise provenance sentence:

> The corrected image is derived from the exact previously submitted MyoPS archive and retains the same five-fold nnU-Net checkpoints and inference configuration. The only change is a preprocessing safeguard that clamps resampled spatial dimensions to at least one voxel; outputs on all 15 normal public validation cases remain bitwise identical to the original image.

Do not attach internal manifests unless the organizers request them. Keep them available in the repository/server evidence packet.
