# CARE-ASE R2 Diagnostic Review Scope Through Step4000

本文件把当前要交给 GPT/外部审阅的训练诊断范围固定为 step4000 及以前。step5000 如果存在，仅作为后续额外诊断文件，不属于本轮主审阅入口。

- primary step: 4000
- included steps: 500, 750, 1000, 2000, 3000, 4000
- scar cases: 88
- pure-edema T2-present cases: 32
- step4000 scar CARE / nnU-Net / MoSAIC: 0.521755 / 0.567299 / 0.754335
- step4000 pure-edema CARE / nnU-Net / MoSAIC: 0.402912 / 0.403784 / 0.405754

| step | scar CARE | scar nnU-Net | scar MoSAIC | edema CARE | edema nnU-Net | edema MoSAIC |
|---:|---:|---:|---:|---:|---:|---:|
| 500 | NA | NA | NA | NA | NA | NA |
| 750 | 0.546037 | 0.567298 | NA | 0.393550 | 0.403823 | NA |
| 1000 | 0.547311 | 0.567306 | NA | 0.393025 | 0.403811 | NA |
| 2000 | 0.544676 | 0.567286 | 0.754335 | 0.391651 | 0.403806 | 0.405754 |
| 3000 | 0.517100 | 0.567277 | 0.754335 | 0.414737 | 0.403807 | 0.405754 |
| 4000 | 0.521755 | 0.567299 | 0.754335 | 0.402912 | 0.403784 | 0.405754 |

Tracked summaries:
- `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step00500_combined_summary.json` sha256 `19d8f7d875cecc9b79af9e45bd2e662c6d71778d131b4aece1a6020fb946c3e9`
- `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step00750_combined_summary.json` sha256 `fab325e117a98ea8ce555a7881a42a567c04bc39c33f30ec70370ac66c108e9e`
- `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step01000_combined_summary.json` sha256 `09f663fea971232343e77d6c45e6fa487d96cf18fa476e68587f9664dba7854d`
- `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step02000_combined_summary.json` sha256 `69f44383d8078fc1273f8f9f85ea7a9f933db3d6f463319ccfec746e0017094f`
- `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step03000_combined_summary.json` sha256 `541ba09f5e6b02ed01565068302f67c487edee702b7f507f593d4b98cbc17b87`
- `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step04000_combined_summary.json` sha256 `2ea01429dca4661c5300ec92def6ded21c3b3868c758e96d94dc587b56d80bb0`

Excluded from this review scope:
- step5000: `results/20260804_care_ase_r2_deadline_recovery_training_docker/outer_diagnostic_step05000_combined_summary.json` exists but is not the current primary upload scope.
