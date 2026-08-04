---
task_key: 20260805_care_myops_single_slice_hotfix_repackage
task_kind: hotfix
task_type: submission_runtime_hotfix
status: AUTHORIZED_BY_USER
risk_level: high
route_change: false
scientific_decision_scope: none
branch_policy: main-only
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 1
executor_count: 1
parallel_execution_allowed: false
executor_plan_path: null
mapper_slots: 1
mapper_required: false
architecture_impact: none
wiki_update_required: true
diagram_update_required: false
slurm_runtime_continuity_required: false
continuity_backend: none
planning_review_required: false
planning_reviewer: none
planning_review_path: null
planning_review_token: null
planning_reviewed_commit: null
review_required: false
review_mode: none
reviewer: none
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_diagnostic_push: false
organizer_email_send_authorized: false
challenge_upload_authorized: false
validation_prediction_upload_authorized: false
corrected_docker_drive_upload_authorized: true
---

# CARE MyoPS Single-Slice Docker Hotfix, Boundary Rehearsal, and Corrected Repackage

## Practical objective

The organizer has confirmed that the submitted CineMyoPS image runs, but the submitted MyoPS image fails on hidden cases with spatial shape `(x, y, 1)`. The observed chain is:

```text
single-slice input
-> nnU-Net preprocessing computes a resampled spatial dimension of 0
-> divide-by-zero / zero-size reduction
-> preprocessing worker dies
-> the container exits before writing the complete prediction set
```

This task must produce a corrected MyoPS Docker by making the smallest possible runtime-only change: preserve the exact submitted model, weights, five-fold ensemble, TTA, label map, input/output contract, and image tag, but ensure every computed resampling dimension is at least one voxel.

The task is not complete after changing one line. It must first reproduce the old failure, then verify the fix on a synthetic geometry boundary matrix, prove exact regression equivalence on all 15 normal public MyoPS cases, test a mixed normal-plus-single-slice batch, clean-save/load the final archive, upload a new corrected archive without overwriting the old one, and create an unsent reply draft.

## Critical provenance boundary

The failed organizer-tested MyoPS artifact is the earlier pure nnU-Net submission, not the later CARE-ASE attempt3 work now present on `main`.

Freeze the failed base artifact as:

```text
archive: MyoPS-OrganAgent.tar.gz
archive_sha256: 638c1d54d1c75f3514f325695025c03bd8f43625c9f2877d72841db6ee2ac73b
archive_size_bytes: 4741640359
loaded_image_tag: care-myocardium-myops:organagent
expected_base_image_id: sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911
submission_contract_commit: 55b95d45554590690c178578ef41712d23aa51c6
```

The model semantics that must remain unchanged are:

```text
nnunetv2: 2.7.0
Dataset501_CAREMyoPS
nnUNetTrainer_500epochs
3d_fullres
folds: 0,1,2,3,4
checkpoint: checkpoint_best.pth
default nnU-Net TTA
raw labels: 0,1,2,3,4,5
official labels: 0,200,500,600,1220,2221
```

Do not build the corrected organizer image from the current mutable directory:

```text
docker/CARE2026_Myocardium/MyoPS
```

That directory has since been repurposed for later CARE-ASE/self-model attempt3 work. Using it would silently change the scientific model and invalidate this hotfix. The corrected image must be a derived image from the exact failed base archive above.

## Fixed workstation environment

Run on the Windows WSL2 workstation where Docker already works without `sudo`:

```text
repo: /home/yuukias/code/CARE
user: yuukias
rclone remote: gdrive:
```

Runtime root:

```text
/home/yuukias/code/CARE/.local_runtime/20260805_care_myops_single_slice_hotfix_repackage
```

Result root:

```text
/home/yuukias/code/CARE/results/20260805_care_myops_single_slice_hotfix_repackage
```

Final local dist:

```text
/home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix
```

Corrected Drive target:

```text
gdrive:/CARE2026_Myocardium_MyoPS_Corrected_20260805/
```

Do not overwrite, delete, retag in place, or replace the previously submitted Drive file.

## Forbidden actions

Do not:

- retrain any model;
- use CARE-ASE, MoSAIC, DG, ARC, PRISM, MyoWall, or any new model overlay;
- change checkpoint, fold, trainer, configuration, TTA, threshold, label map, postprocessing, or input channel order;
- upgrade or downgrade nnU-Net, Python, PyTorch, NumPy, SciPy, scikit-image, or any dependency;
- rebuild or resubmit CineMyoPS;
- alter the old MyoPS archive;
- upload predictions, ground truth, validation data, or challenge data;
- send the organizer email;
- read, print, copy, commit, or return `rclone.conf`, OAuth tokens, refresh tokens, or secrets;
- commit Docker archives, checkpoints, NIfTI files, runtime directories, generated predictions, or large logs;
- use `/overflow/htzhu/CARE`.

## Phase 1 — Sync and re-ground

```bash
cd /home/yuukias/code/CARE
git fetch --all --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -20
git diff --check
```

If the tree is clean and behind:

```bash
git pull --ff-only origin main
```

Read:

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
results/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/revised_final_submission_model_contract.json
results/20260803_care_test_docker_workstation_build_validate_return/**
results/20260803_care_test_docker_official_submission_resume_after_rclone/**
results/20260803_care_test_docker_server_final_submission_readiness_confirm/**
prompts/tasks/20260805_care_myops_single_slice_hotfix_repackage_controller.md
```

The current `CURRENT.md` may contain newer CARE-ASE state above the older Docker sections. Do not overwrite that state. Add a separate MyoPS organizer-runtime-hotfix section only after the task reaches a verified terminal result.

## Phase 2 — Locate and freeze the failed base archive

Preferred local path:

```text
/home/yuukias/code/CARE/dist/20260803_care_test_docker_final/MyoPS-OrganAgent.tar.gz
```

If absent, recover the exact file from the existing Drive folder using `gdrive:`. Do not use a similarly named attempt3 archive.

Before loading:

```bash
stat -c '%n|%s' <base-archive>
sha256sum <base-archive>
```

Require exact size and SHA from the provenance boundary. Then:

```bash
docker load --input <base-archive>
docker image inspect care-myocardium-myops:organagent
```

Require image ID:

```text
sha256:52f8d872a51c482d488e3d2a14893958a6b1d6c8c91fffed9985ee330fcec911
```

Freeze it under an internal-only base tag:

```bash
docker tag care-myocardium-myops:organagent care-myocardium-myops:attempt2-base
```

Record archive SHA, image ID, architecture, OS, ENTRYPOINT, dependency versions, and five checkpoint hashes in:

```text
base_artifact_provenance.json
```

If any expected field differs, stop with:

```text
BASE_ARTIFACT_PROVENANCE_MISMATCH
```

## Phase 3 — Reproduce the organizer failure before patching

### 3.1 Inspect the exact installed nnU-Net source

Run inside the base image without altering it:

```bash
docker run --rm --entrypoint python care-myocardium-myops:attempt2-base - <<'PY'
import hashlib
import importlib.metadata as md
import inspect
from pathlib import Path
import nnunetv2.preprocessing.resampling.default_resampling as r

p = Path(inspect.getsourcefile(r)).resolve()
print('nnunetv2', md.version('nnunetv2'))
print('source', p)
print('sha256', hashlib.sha256(p.read_bytes()).hexdigest())
print(inspect.getsource(r.compute_new_shape))
PY
```

Require `nnunetv2==2.7.0`. Record the original source path, SHA, and function text.

### 3.2 Build a real single-slice reproducer from public data

Locate the prior full public rehearsal input tree. If it no longer exists locally, copy only the public MyoPS input data from the approved server runtime. Never copy GT.

Select a public case with clearly present central anatomy. Use a three-dimensional `SimpleITK.RegionOfInterest` extraction, not `ExtractImageFilter`, so the result remains a 3D image with depth one.

For LGE, T2, and C0, extract the same central slice and preserve direction/origin. Create at least these aligned synthetic cases under an official root:

```text
/input/myops/SS_Z1_SP1_*.nii.gz      depth=1, z-spacing=1.0
/input/myops/SS_Z1_SP4_*.nii.gz      depth=1, z-spacing=4.0
/input/myops/SS_Z1_SP5_*.nii.gz      depth=1, z-spacing=5.0
/input/myops/SS_Z1_SP9P9_*.nii.gz    depth=1, z-spacing=9.9
/input/myops/SS_Z1_SP10_*.nii.gz     depth=1, z-spacing=10.0
/input/myops/SS_Z1_SP20_*.nii.gz     depth=1, z-spacing=20.0
/input/myops/SS_Z2_SP1_*.nii.gz      depth=2, z-spacing=1.0
/input/myops/SS_Z2_SP4_*.nii.gz      depth=2, z-spacing=4.0
/input/myops/SS_TINY_Z1_*.nii.gz     central in-plane ROI, at least 64x64x1
```

Use the exact filename suffixes `_LGE.nii.gz`, `_T2.nii.gz`, `_C0.nii.gz`.

Write a generator script and manifest recording source case, slice index, ROI, size, spacing, origin, direction, modality hashes, and geometry equality.

### 3.3 Negative control

First test `compute_new_shape` directly in the unpatched base image on shapes/spacings that should round to zero. At least one result must contain a zero dimension.

Then run the unpatched base image on the synthetic root with `--network none` and read-only input. Capture exit code and full stdout/stderr. The negative control must reproduce an end-to-end failure on at least one depth-one/depth-two low-spacing case, with evidence consistent with one or more of:

```text
divide by zero encountered in divide
zero-size array to reduction operation maximum
background worker died
some background workers are no longer alive
```

If the direct function produces a zero but the full container does not fail, expand the spacing matrix based on the image's actual transposed spacing and plans target spacing until an end-to-end reproducer is obtained.

If no faithful reproducer can be created, stop with:

```text
REPRODUCER_MISMATCH_NEEDS_TRACE
```

Do not blindly patch and claim the organizer bug fixed.

Write:

```text
organizer_failure_reproducer.json
organizer_failure_reproducer.md
base_failure_stdout.log
base_failure_stderr.log
```

## Phase 4 — Implement the minimal derived-image hotfix

Create a new lightweight context:

```text
docker/CARE2026_Myocardium/MyoPS_attempt2_single_slice_hotfix/
```

It must contain only:

```text
Dockerfile
apply_single_slice_hotfix.py
README.md
```

The Dockerfile must derive from the frozen local image:

```dockerfile
FROM care-myocardium-myops:attempt2-base
COPY apply_single_slice_hotfix.py /tmp/apply_single_slice_hotfix.py
RUN python /tmp/apply_single_slice_hotfix.py \
 && rm /tmp/apply_single_slice_hotfix.py
LABEL org.opencontainers.image.description="CARE MyoPS attempt2 single-slice preprocessing hotfix"
```

No `pip install`, `apt`, remote download, dependency update, model copy, checkpoint replacement, or network access is allowed.

The patch script must:

1. require `nnunetv2==2.7.0`;
2. locate the installed `nnunetv2.preprocessing.resampling.default_resampling` source file;
3. verify the pre-patch function is the expected unmodified 2.7.0 implementation;
4. replace only the return path of `compute_new_shape` so that existing rounding is preserved and each dimension is clamped to at least one:

```python
new_shape = np.array([
    int(round(i / j * k))
    for i, j, k in zip(old_spacing, new_spacing, old_shape)
])
new_shape = np.maximum(new_shape, 1)
return new_shape
```

5. make no other nnU-Net source modification;
6. compile/import the patched module;
7. write `/app/hotfix/single_slice_hotfix_receipt.json` containing package version, original source SHA, patched source SHA, exact replacement count, function source after patch, and timestamp;
8. fail closed if the expected source pattern occurs zero times or more than once.

The fix must not change the old image ENTRYPOINT, command, environment variables, weights, model files, or output paths.

Build with no pull and no network dependency:

```bash
docker build --pull=false \
  -t care-myocardium-myops:single-slice-hotfix \
  docker/CARE2026_Myocardium/MyoPS_attempt2_single_slice_hotfix
```

## Phase 5 — Static and direct-function verification

Inside the patched image, verify:

- `nnunetv2==2.7.0`;
- all five `checkpoint_best.pth` files remain present with the original SHA values;
- ENTRYPOINT unchanged;
- the hotfix receipt exists;
- no CARE-ASE/self-model files were introduced;
- no package version changed.

Directly test `compute_new_shape` for a matrix that includes:

```text
old_shape=(1,256,256), old_spacing z in {1,4,5,9.9,10,20,50}
old_shape=(2,256,256), old_spacing z in {1,4,5,10,20}
old_shape=(1,1,1), old_spacing=(1,1,1), new_spacing=(10,10,10)
axis permutations where the singleton dimension is axis 0, 1, and 2
```

Every returned dimension must be an integer >= 1. For inputs whose old implementation already produced all-positive dimensions, the patched result must exactly equal the old result.

Write:

```text
compute_new_shape_boundary_matrix.csv
hotfix_source_receipt.json
image_asset_invariance_receipt.json
```

## Phase 6 — End-to-end single-slice and mixed-batch tests

### 6.1 Synthetic edge matrix

Run the patched image on all synthetic cases together:

```bash
docker run --rm --network none \
  -v <synthetic-official-root>:/input:ro \
  -v <synthetic-output-root>:/output \
  care-myocardium-myops:single-slice-hotfix
```

Hard requirements:

- exit code 0;
- one and only one output for every synthetic case;
- no missing/duplicate/unknown output;
- output path `/output/myops/<CaseID>_pred.nii.gz`;
- output remains 3D;
- depth equals the original input depth for depth-one and depth-two cases;
- shape, spacing, origin, and direction exactly match LGE;
- SimpleITK and nibabel both read every file;
- finite integer-valued labels only;
- allowed labels subset `{0,200,500,600,1220,2221}`;
- no temporary files left in `/output` root;
- input hashes unchanged;
- no divide-by-zero, zero-size, or dead-worker message.

Choose the source central slice so that the representative cases `SS_Z1_SP4`, `SS_Z1_SP5`, and `SS_Z1_SP10` contain non-background anatomy. Require at least one of labels `200/500/600` in each of those three representative outputs. Record pathology labels but do not require scar/edema to be present on every synthetic slice.

### 6.2 Full normal-case regression equivalence

Use all 15 public MyoPS cases.

Preferred baseline: reuse the old organizer-tested image's retained 15-case outputs from the prior full rehearsal. If those arrays are unavailable, rerun the frozen base image on all 15 cases.

Run the patched image once on the same 15 cases. Require for every case:

- exact voxel-array equality between base and patched output;
- exact shape, spacing, origin, direction;
- exact allowed label set;
- exact output case set;
- exit code 0.

This gate proves the hotfix changes only the previously invalid zero-dimension boundary and does not alter normal multi-slice predictions.

### 6.3 Mixed batch

Build one official root containing all 15 public cases plus the full synthetic edge matrix. Run the patched image once. Require exactly the union of expected outputs and exit code 0. This is mandatory because the organizer failure aborted the complete batch after one bad case.

### 6.4 Determinism

Run at least these cases twice from the same patched image:

```text
SS_Z1_SP4
SS_Z2_SP1
one normal multi-slice public case
```

Require exact array and geometry equality.

Write:

```text
single_slice_edge_casewise.csv
single_slice_edge_summary.json
normal_15case_regression_casewise.csv
normal_15case_regression_summary.json
mixed_batch_casewise.csv
mixed_batch_summary.json
patched_determinism_casewise.csv
```

## Phase 7 — Failure-mode expansion

Do not assume fixing one zero dimension prevents all geometry failures. Add fail-closed tests for:

- zero or negative spacing: container must reject with a clear nonzero error;
- non-finite spacing/metadata if it can be represented: reject clearly;
- modality geometry mismatch: reject and report case ID;
- missing T2/C0/LGE: reject and report case ID/modality;
- empty `/input/myops`: reject, no fake output;
- output task directory absent initially: create it;
- unrelated file already under `/output`: preserve it;
- read-only input: succeed without modification;
- multiple single-slice cases in one batch: all outputs produced.

These negative tests must not modify the scientific model. If the inherited wrapper already fails clearly, record the behavior rather than adding unrelated code. Only add a wrapper preflight if a valid hidden-like input still reaches an avoidable cryptic worker crash after the shape clamp.

## Phase 8 — Clean save/load and final archive

After all gates pass:

```bash
docker tag \
  care-myocardium-myops:single-slice-hotfix \
  care-myocardium-myops:organagent
```

Save deterministically:

```bash
mkdir -p /home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix

docker save care-myocardium-myops:organagent \
  | gzip -n \
  > /home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix/MyoPS-OrganAgent-corrected.tar.gz

sha256sum \
  /home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix/MyoPS-OrganAgent-corrected.tar.gz \
  > /home/yuukias/code/CARE/dist/20260805_care_myops_single_slice_hotfix/MyoPS-OrganAgent-corrected.tar.gz.sha256
```

Record size and SHA. Remove only the corrected final tag, reload from the new archive, and verify:

- exact final tag;
- expected patched image ID;
- linux/amd64;
- unchanged ENTRYPOINT;
- hotfix receipt present;
- five checkpoints present and unchanged.

From the clean-loaded archive rerun:

- the entire synthetic edge matrix;
- one mixed batch containing at least one normal and two single-slice cases;
- one normal public case and compare to the old base output.

Do not declare completion based only on the pre-save image.

## Phase 9 — Upload corrected archive and verify public access

Only after all Docker gates pass, upload these new files to a new Drive folder:

```text
MyoPS-OrganAgent-corrected.tar.gz
MyoPS-OrganAgent-corrected.tar.gz.sha256
single_slice_hotfix_public_receipt.json
```

Use the already configured persistent `gdrive:` remote. Do not print or read its config.

Run `rclone copy`, then verify remote size and MD5/hash where supported. Generate a new public link with `rclone link`. Check it without authentication using `curl -L -I`; status must not be 401/403/404. Do not reuse the old failed MyoPS URL.

Write:

```text
google_drive_corrected_upload_receipt.json
google_drive_corrected_public_link.json
```

The upload and public link must correspond to the corrected archive's new size and SHA.

CineMyoPS is unchanged and must not be re-uploaded or rebuilt in this task.

## Phase 10 — Organizer reply draft, but do not send

Create:

```text
results/20260805_care_myops_single_slice_hotfix_repackage/organizer_reply_draft.md
```

Use a concise, natural reply. It must state:

- the single-slice preprocessing issue has been corrected;
- only MyoPS is updated;
- CineMyoPS remains unchanged;
- corrected download link, archive name, image tag, size, and SHA256;
- same no-extra-command load/run contract;
- the corrected archive was tested on depth-one/depth-two geometry cases, a mixed batch, and all 15 public MyoPS cases;
- normal 15-case outputs were exactly unchanged from the prior image;
- request reevaluation.

Do not include internal development history, model scores, CARE-ASE discussion, or promotional wording. Do not send the email.

## Phase 11 — Strict validator

Add:

```text
scripts/validation/validate_care_myops_single_slice_hotfix_repackage.py
```

It must fail closed on at least these known-bad conditions:

- base archive SHA/size/image ID mismatch;
- current CARE-ASE attempt3 context used as the corrected organizer image;
- any model/checkpoint/TTA/label-map/dependency change;
- patch source pattern not uniquely matched;
- `compute_new_shape` can still return zero;
- no faithful old-image negative control;
- only direct function tests, without a real Docker single-slice run;
- depth-one tested but depth-two omitted;
- no low-spacing cases around the rounding boundary;
- no mixed normal-plus-single-slice batch;
- not exactly 15 public normal outputs;
- patched normal output differs from base output;
- output depth/geometry differs from input;
- unknown/non-integer labels;
- all representative central-slice outputs are background only;
- input modified;
- pre-save image tested but clean-loaded archive not tested;
- wrong final image tag or empty ENTRYPOINT;
- five checkpoint hashes changed;
- old failed Drive link reused;
- corrected public link unverified;
- Cine rebuilt or changed;
- organizer email sent;
- predictions, GT, archive, checkpoint, rclone config, or secret staged in Git.

Run known-bad fixtures that deliberately remove the clamp, alter one checkpoint receipt, skip the mixed batch, and point the reply draft to the old URL. Each must fail.

## Phase 12 — Results, server return, Git, and notifier

Create lightweight results:

```text
results/20260805_care_myops_single_slice_hotfix_repackage/
  controller_context.json
  controller_ledger.csv
  base_artifact_provenance.json
  organizer_failure_reproducer.json
  organizer_failure_reproducer.md
  hotfix_source_receipt.json
  compute_new_shape_boundary_matrix.csv
  image_asset_invariance_receipt.json
  synthetic_input_manifest.json
  single_slice_edge_casewise.csv
  single_slice_edge_summary.json
  normal_15case_regression_casewise.csv
  normal_15case_regression_summary.json
  mixed_batch_casewise.csv
  mixed_batch_summary.json
  patched_determinism_casewise.csv
  clean_save_load_receipt.json
  corrected_archive_manifest.json
  google_drive_corrected_upload_receipt.json
  google_drive_corrected_public_link.json
  organizer_reply_draft.md
  strict_validator_report.json
  controller_report.md
  completion_check.md
  MANIFEST.md
  notification_brief.json
```

Return a lightweight packet to the existing CARE server under:

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260805_care_myops_single_slice_hotfix_repackage/
```

Do not block the corrected Drive link on retransferring the multi-gigabyte archive to the server. The corrected archive may remain on the workstation and Drive; the server must receive the manifest, SHA, public-link receipt, reproducer, regression evidence, validator report, and reply draft.

Update `prompts/routes/handoffs/CURRENT.md` and `wiki/README.md` with a separate section. Do not overwrite newer CARE-ASE training state. The new section must say the earlier MyoPS Docker failed organizer hidden single-slice input, the corrected derived image was tested, and the organizer reply remains unsent.

Commit only lightweight source, tests, prompt, validator, receipts, and state documentation. Before commit:

```bash
git fetch origin main --prune
git status --short
git diff --check
```

Forbidden staged suffixes/paths include:

```text
*.pt
*.pth
*.nii
*.nii.gz
*.tar
*.tar.gz
.local_runtime/
dist/
rclone.conf
*token*
*secret*
```

If `origin/main` advanced because of parallel CARE-ASE work, rebase the lightweight hotfix commit without overwriting that work.

Commit message:

```text
package: harden MyoPS Docker for single-slice inputs
```

Push `origin/main`, verify `HEAD == origin/main`, then call the existing notifier through the server. Do not create a custom SMTP sender.

## Terminal completion gate

The only successful terminal state is:

```text
CORRECTED_MYOPS_DOCKER_READY_FOR_ORGANIZER_REEVALUATION
```

It requires all of:

```text
base_artifact_exact=true
old_failure_reproduced=true
single_slice_clamp_minimum_one=true
synthetic_depth1_depth2_matrix_pass=true
normal_15case_exact_regression=true
mixed_batch_complete=true
patched_determinism=true
clean_archive_reload_pass=true
checkpoint_hashes_unchanged=true
corrected_drive_upload_pass=true
corrected_public_link_verified=true
organizer_reply_draft_ready=true
organizer_email_sent=false
strict_validator=PASS
git_commit_push_complete=true
```

If any item fails, return a precise non-ready status and do not suggest sending the corrected link.

## Final response

Start with a natural Chinese judgment and report:

1. whether the old hidden-like failure was reproduced;
2. exact root cause and patched source SHA;
3. exact patch scope;
4. depth-one/depth-two boundary matrix results;
5. mixed-batch result;
6. 15-case exact regression result;
7. clean save/load result;
8. corrected archive path, size, SHA, and image ID;
9. corrected public Drive link and unauthenticated check;
10. organizer reply draft path;
11. Git commit/push SHA;
12. explicit confirmation that no model semantics, Cine archive, validation predictions, challenge data, or organizer email were changed/sent.
