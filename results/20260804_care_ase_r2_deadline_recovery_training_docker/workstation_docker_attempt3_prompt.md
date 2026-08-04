# Workstation / WSL Docker handoff: CARE2026 MyoPS attempt3 + Cine MoSAIC

目标：构建 MyoPS attempt3 Docker archive；CineMyoPS 继续使用已保存的 MoSAIC archive。不要重新训练，不要改 label map，不要发送组织方邮件，不要上传 validation predictions。

服务器 transfer 目录：
`/users/a/e/aereinh/.tmp/codex-CARE/20260804_care_ase_r2_deadline_recovery_training_docker/attempt3_docker_transfer`

需要复制到工位电脑的文件：

- `MyoPS-attempt3-self-model-workstation-bundle.tar.gz`
  - SHA256: `98e4ff2e9123a66c05230a54ca5a9f55eda906bf96634274c07b1e7ef8aaa97f`
- `CineMyoPS-OrganAgent.tar.gz`
  - SHA256: `c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136`
- `WORKSTATION_HANDOFF_ATTEMPT3.json`

## MyoPS build

```bash
mkdir -p ~/care_attempt3_myops
cd ~/care_attempt3_myops
sha256sum MyoPS-attempt3-self-model-workstation-bundle.tar.gz
# must equal 98e4ff2e9123a66c05230a54ca5a9f55eda906bf96634274c07b1e7ef8aaa97f
tar -xzf MyoPS-attempt3-self-model-workstation-bundle.tar.gz -C .
cd workstation_bundle_root/contexts/MyoPS
docker build -t care-myocardium-myops:attempt3 .
```

Run the official 15-case MyoPS black-box rehearsal with `/input` mounted to the official MyoPS validation input root and `/output` mounted to an empty output directory:

```bash
mkdir -p ~/care_attempt3_myops/output
docker run --rm \
  -v /path/to/MyoPS_validation_input:/input:ro \
  -v ~/care_attempt3_myops/output:/output \
  care-myocardium-myops:attempt3
```

Expected output: exactly 15 files under `~/care_attempt3_myops/output/myops`, named `<CaseID>_pred.nii.gz`. Labels must be official values only: `0, 200, 500, 600, 1220, 2221`.

Save and hash:

```bash
docker save care-myocardium-myops:attempt3 | gzip -n > CARE2026_MyoPS_attempt3_self_model.tar.gz
sha256sum CARE2026_MyoPS_attempt3_self_model.tar.gz > CARE2026_MyoPS_attempt3_self_model.tar.gz.sha256
```

## CineMyoPS

Do not rebuild unless necessary. Reuse `CineMyoPS-OrganAgent.tar.gz` byte-for-byte. Verify:

```bash
sha256sum CineMyoPS-OrganAgent.tar.gz
# must equal c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136
```

## Return to server/user

Return:

- MyoPS archive size and SHA256;
- Cine archive SHA256 confirmation;
- MyoPS 15-case output count and label audit summary;
- any Docker build/run error logs if failed.
