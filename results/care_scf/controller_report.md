CARE-SCF 目前不能作为真实激活的 final-submission candidate：nnU-Net 5-fold anchor 已有完整 OOF 预测，但 MoSAIC 只有 fold0 公平复现的 44 例证据，fold1-fold4 的 fold-specific checkpoint/prediction 缺失。为了避免把 full-data/pretrained MoSAIC 输出误当成 cross-fitted evidence，本 packet 没有训练 CARE gate，也没有生成 SafeScar/SCF 替代预测；当前结论是保留 nnU-Net control，不提交 CARE-SCF validation。

## Answers

1. MoSAIC 与 nnU-Net 的互补性：fold0 上存在有限互补，scar 有 9 个 MoSAIC help、33 个 harm、2 个 tie；pure_edema 只有 1 个 help、15 个 harm，另有 28 个 GT-empty 不适合作为可靠改善证据。
2. CARE-SCF 是否真实激活：否。`care_scf_real_activation=false`，因为 fold1-fold4 MoSAIC OOF 和 probability/prototype feature 未完成。
3. 哪些病例改善：仅 fold0 diagnostic oracle 中 `component_decisions.csv` 的 scar `diagnostic_oracle_action=replace` 可视为候选改善病例；这些不是已激活 SCF 输出。
4. 哪些病例受损：fold0 diagnostic oracle 中 scar `help_harm=harm` 有 33 行，pure_edema `help_harm=harm` 有 15 行；详见 `help_harm.csv`。
5. 是否值得提交 validation：不值得提交 CARE-SCF。当前只有 nnU-Net control 可作为已完成 anchor；CARE-SCF 缺 cross-fitted MoSAIC component evidence，提交会不可解释且高风险。

## Key Files

- `results/care_scf/final_manifest.json`
- `results/care_scf/provenance.json`
- `results/care_scf/mosaic_oof_status.csv`
- `results/care_scf/component_dataset_fold0_diagnostic.csv`
- `results/care_scf/component_decisions.csv`
- `results/care_scf/care_gate_training_receipt.json`
- `results/care_scf/care_prediction_status.csv`
- `results/care_scf/completion_audit.csv`
- `results/care_scf/help_harm.csv`
- `results/care_scf/geometry_audit.csv`
