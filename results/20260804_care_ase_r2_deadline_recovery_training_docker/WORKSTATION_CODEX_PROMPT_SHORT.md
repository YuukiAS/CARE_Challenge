进入工位电脑的 CARE 工作区后，读取并严格执行这个文件：

`results/20260804_care_ase_r2_deadline_recovery_training_docker/WORKSTATION_DOCKER_ATTEMPT3_REQUIREMENTS.md`

不要重新训练，不要改模型/threshold/label map，不要上传 validation predictions 或 Docker archive，不要发组织方邮件。你的任务只是按该文件完成 MyoPS attempt3 Docker build、15-case official-input 黑盒彩排、label audit、docker save/gzip/hash，并复核 CineMyoPS MoSAIC archive SHA。完成后写 `attempt3_workstation_result.json`、`attempt3_workstation_result.md`、`attempt3_myops_label_audit.csv`，并把 MyoPS archive SHA/size、Cine SHA、15-case 输出数量和任何失败日志返回。
