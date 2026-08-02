这次服务器端修订已经把 MyoPS 从旧的混合方案改成纯五折 nnU-Net，并把 CineMyoPS 固定为合作者提供的原始 Docker archive。服务器没有运行 Docker，也没有上传 challenge/validation 或给组织方发邮件；新 transfer 只授权工位 WSL 做 build/load/run。

- 任务: `20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle`
- supersedes: `c2f946b9376f4b39700f04b39c6d7a16e7154e67`
- MyoPS: Dataset501_CAREMyoPS, nnUNetTrainer_500epochs, 3d_fullres, folds 0-4, checkpoint_best.pth, default TTA
- CineMyoPS archive SHA256: `c02db56bd52d14d3b5bbda9d204a20b7e4c061fd5e6012ffa1cebc67fb92c136`
- collaborator MyoPS reference SHA256: `81d19bbefd8f7cca46aee32b31a774f16222b6146b9eab6bc7265a6c214de2ff`
- 复用 fresh nnU-Net 15 例 raw outputs: `/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_test_docker_cross_machine/fresh_nnunet_myops`
- sentinel cases: Case1012, Case1001, Case1004
- transfer: `/users/a/e/aereinh/.tmp/codex-CARE/20260802_care_test_docker_nnunet_myops_collaborator_cine_rebundle/transfer`
