# CARE2026 Workstation Docker Attempt3 Requirements

status: READY_FOR_WORKSTATION_DOCKER_BUILD

This file is the authoritative workstation-side handoff for CARE2026 MyoPS
attempt3 and CineMyoPS reuse. Follow it exactly. Do not infer requirements from
chat history.

## Scope

Build and verify the MyoPS attempt3 Docker archive on the workstation or WSL.
Reuse the existing CineMyoPS MoSAIC Docker archive byte-for-byte.

## Server Transfer Directory

```text
/users/a/e/aereinh/.tmp/codex-CARE/20260804_care_ase_r2_deadline_recovery_training_docker/attempt3_docker_transfer
```

Copy these files from the server transfer directory to the workstation working
directory:

```text
MyoPS-attempt3-self-model-workstation-bundle.tar.gz
MyoPS-attempt3-self-model-workstation-bundle.tar.gz.sha256
CineMyoPS-OrganAgent.tar.gz
CineMyoPS-OrganAgent.tar.gz.sha256
WORKSTATION_HANDOFF_ATTEMPT3.json
WORKSTATION_PROMPT_ATTEMPT3.md
```

## Fixed Hashes

MyoPS bundle:

```text
98e4ff2e9123a66c05230a54ca5a9f55eda906bf96634274c07b1e7ef8aaa97f  MyoPS-attempt3-self-model-workstation-bundle.tar.gz
```

CineMyoPS archive:

```text
c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136  CineMyoPS-OrganAgent.tar.gz
```

If either hash differs, stop and report the mismatch. Do not rebuild from a
mismatched input.

## Model Semantics

MyoPS attempt3:

- nnU-Net provides anatomy labels and geometry restoration.
- CARE-ASE step500 fold1/fold4 self-model checkpoint ensemble provides scar and
  pure-edema overlay.
- nnU-Net is not a scar/edema submission candidate in this attempt; it is used
  only for anatomy, preprocessing, geometry, and comparison support.
- Official raw labels are mapped to official labels:

| Raw | Official |
| --- | --- |
| 0 | 0 |
| 1 | 200 |
| 2 | 500 |
| 3 | 600 |
| 4 | 1220 |
| 5 | 2221 |

CineMyoPS:

- Reuse `CineMyoPS-OrganAgent.tar.gz` byte-for-byte.
- Do not rebuild CineMyoPS unless the copied archive is missing or hash-invalid.

## Forbidden Actions

Do not:

- retrain any model;
- change checkpoint, fold, TTA, label map, threshold, postprocessing rule, or
  model selection;
- overwrite or regenerate the existing CineMyoPS archive;
- upload validation predictions;
- upload Docker archives unless explicitly instructed later;
- send organizer email;
- delete fallback archives;
- use nnU-Net as the scar/edema submission candidate.

## MyoPS Build Commands

Run on the workstation or WSL after copying the transfer files:

```bash
mkdir -p ~/care_attempt3_myops
cd ~/care_attempt3_myops
sha256sum MyoPS-attempt3-self-model-workstation-bundle.tar.gz
# must equal 98e4ff2e9123a66c05230a54ca5a9f55eda906bf96634274c07b1e7ef8aaa97f
tar -xzf MyoPS-attempt3-self-model-workstation-bundle.tar.gz -C .
cd workstation_bundle_root/contexts/MyoPS
docker build -t care-myocardium-myops:attempt3 .
```

## Required Context Inspection Before Build

Before `docker build`, verify:

```bash
test -f Dockerfile
test -f predict.py
test -f models/self_model/selection.json
test -f models/self_model/care_ase_01_checkpoint_step00500.pt
test -f models/self_model/care_ase_01_checkpoint_step00500.pt.sha256
test -f models/self_model/care_ase_02_checkpoint_step00500.pt
test -f models/self_model/care_ase_02_checkpoint_step00500.pt.sha256
test -f care_ase_vendor/src/src/care_myocardium/models/care_ase.py
test -f care_ase_vendor/src/src/care_myocardium/inference/care_ase_r2_full_volume.py
test -f care_ase_vendor/data/data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json
test -f care_ase_vendor/data/data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json
```

Also confirm `Dockerfile` contains:

```text
COPY care_ase_vendor/src /app/src
COPY care_ase_vendor/data /app/src/data
COPY models /app/models
```

## Official 15-Case MyoPS Black-Box Rehearsal

Run the container against the official 15-case MyoPS validation input root:

```bash
mkdir -p ~/care_attempt3_myops/output
docker run --rm \
  -v /path/to/MyoPS_validation_input:/input:ro \
  -v ~/care_attempt3_myops/output:/output \
  care-myocardium-myops:attempt3
```

Replace `/path/to/MyoPS_validation_input` with the workstation's actual official
MyoPS validation input directory. It must contain exactly the official 15 public
validation cases, with each case providing LGE, T2, and C0 files.

Required output:

```text
~/care_attempt3_myops/output/myops/<CaseID>_pred.nii.gz
```

There must be exactly 15 output files. There must be no missing case, duplicate
case, or unknown case.

## Output Label Audit

Run a label audit over all 15 outputs. Accepted label values only:

```text
0, 200, 500, 600, 1220, 2221
```

For each case, record:

- case_id;
- output path;
- output SHA256;
- image shape, spacing, origin, direction;
- voxel counts for each label;
- whether scar label 2221 is present;
- whether edema label 1220 is present.

If any unexpected label appears, stop and report failure.

## Archive Save and Hash

If build and 15-case rehearsal pass:

```bash
cd ~/care_attempt3_myops
docker save care-myocardium-myops:attempt3 | gzip -n > CARE2026_MyoPS_attempt3_self_model.tar.gz
sha256sum CARE2026_MyoPS_attempt3_self_model.tar.gz > CARE2026_MyoPS_attempt3_self_model.tar.gz.sha256
ls -lh CARE2026_MyoPS_attempt3_self_model.tar.gz
```

Do not upload the archive unless explicitly instructed later.

## CineMyoPS Verification

Verify the copied CineMyoPS archive:

```bash
sha256sum CineMyoPS-OrganAgent.tar.gz
# must equal c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
```

No Cine rebuild is required if the hash matches.

## Required Return Packet

Return a concise packet to the server/user containing:

- MyoPS build status;
- MyoPS 15-case run status;
- MyoPS output count;
- MyoPS label audit summary;
- MyoPS archive path, size, and SHA256;
- CineMyoPS archive path, size, and SHA256;
- any failed command and log excerpt if a command fails;
- confirmation that no validation predictions, Docker archive, or organizer
  email were uploaded/sent.

Recommended file names on workstation:

```text
attempt3_workstation_result.json
attempt3_workstation_result.md
attempt3_myops_label_audit.csv
```

## Failure Handling

If any command fails, do not silently patch model behavior. Capture:

- command;
- exit code;
- working directory;
- relevant stdout/stderr tail;
- whether any archive was created;
- whether any upload/email happened.

Then report the failure back to the server/user.
