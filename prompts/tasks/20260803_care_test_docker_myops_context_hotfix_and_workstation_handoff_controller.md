---
task_key: 20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff
project: CARE
role: controller
branch_policy: main-only
status: ready
allow_code_change: true
allow_shell_command: true
allow_network: false
allow_external_upload: false
requires_human_approval: false
---

# CARE 2026 Myocardium Docker Resource Hotfix And Workstation Handoff

This task hotfixes the server-side MyoPS workstation Docker context produced by
commit `b94d3f916b04461d6b88a311959e0ed581e64555`.

## Fixed Model Contract

MyoPS remains unchanged:

- `Dataset501_CAREMyoPS`
- `nnunetv2==2.7.0`
- Python `3.12.13`
- PyTorch `2.11.0`
- `nnUNetTrainer_500epochs`
- `3d_fullres`
- folds `0,1,2,3,4`
- `checkpoint_best.pth`
- default TTA
- raw `0/1/2/3/4/5` maps directly to official `0/200/500/600/1220/2221`

CineMyoPS remains the collaborator byte-preserved Docker save archive:

- `CineMyoPS-OrganAgent.tar.gz`
- image tag `care-myocardium-cinemyops:organagent`
- SHA256 `c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136`

## Hotfix

`docker/CARE2026_Myocardium/MyoPS/Dockerfile` must copy `models/` into
`/app/models`, because `predict.py` resolves nnU-Net checkpoints under
`/app/models/nnunet/nnUNet_results`.

The Dockerfile must not copy MoSAIC source or weights, must not add runtime model
downloads, must not change folds/checkpoint/TTA/trainer/configuration/label map,
and must not reference server absolute model paths.

## Outputs

Write lightweight evidence under:

`results/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff`

Write runtime transfer artifacts under:

`/users/a/e/aereinh/.tmp/codex-CARE/20260803_care_test_docker_myops_context_hotfix_and_workstation_handoff/transfer`

Do not commit checkpoints, NIfTI files, Docker archives, transfer tarballs,
downloads, runtime directories, or large logs.

Close out with strict validator, commit, push `origin/main`, remote SHA
verification, and the existing notifier.
