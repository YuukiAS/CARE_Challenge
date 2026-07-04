# Review 20260704 Anchor SRR Forensic Repro Audit

audit_status: completed
auditor_role: Codex forensic review session
forensic_decision: PARTIAL_REPRODUCIBLE
experiment_adequacy_decision: PASS_FOR_CURRENT_PACKET
route_promotion_decision: NO_PROMOTION
route_negative_decision: STOP_SUPPORTED_FOR_CURRENT_ANCHORED_PACKET_ONLY
scientific_resolution_status: SCIENTIFIC_STOP_SUPPORTED_FOR_CURRENT_PACKET
next_state: STOP

## 审阅结论

当前 `HEAD=39f9a573b1db33bbf99880d63c0d40a9cd7a1d8e` 已经包含 `Implement anchored SRR v2.5 diagnostics`，比 `origin/main` ahead 1；工作树在审阅开始时无 tracked dirt。这个状态不是任务开头怀疑的旧状态：提交源码中的 `SRRProposeRefineMyoPS.forward` 确实接收 `anchor_features` 和 `component_features`，训练、one-batch、验证/预测路径也确实把 nnU-Net anchor/component 传入 `model(...)`。

但旧诊断包不能升级为 `REPRODUCIBLE_AND_SUPPORTED`。它只达到 `PARTIAL_REPRODUCIBLE`：核心 anchor/component 消费、多槽 retrieval、soft ROI crop refinement、no-T2 edema guardrail 和 same-split negative metrics 有提交级证据；完整 data-derived prototype bank、CineMA 完整尝试、registration option matrix 仍是 partial/missing。当前 STOP 只能支持“停止这个已审阅 anchored SRR fold0 packet 作为 challenge-facing 候选”，不能写成 SRR 架构方向已经被科学穷尽。

## 关键发现

1. `jobs/src/run_myops_anchor_srr_fold0_formal.sh` 将 Slurm array `MyoPSAnchorSRRF0` 映射到三组 variant，并写出 `run_config.env`。`job_status.md` 记录 `57782213/57782214/57782211` 三个 array task 都完成并有 summary。
2. 三份 Slurm log 文件存在但都是 0 字节：`logs/MyoPSAnchorSRRF0_0_57782213_20260704_022627.log`、`logs/MyoPSAnchorSRRF0_1_57782214_20260704_022627.log`、`logs/MyoPSAnchorSRRF0_2_57782211_20260704_022627.log`。因此 stdout/stderr 不能作为 transcript；可用替代证据是 committed `run_config.env`、`summary.json`、`job_status.md`、`experiment_adequacy_report.md` 和源代码。
3. `summary.json` 和 `run_config.env` 已被 git 跟踪；checkpoints、predictions/NIfTI 和 logs 是被 `.gitignore` 排除的 runtime/heavy evidence，不应为诊断发布强行提交。
4. 当前 fold0 证据低于同 split nnU-Net baseline：scar all-case Dice 最好 `0.4183` vs baseline `0.5602`；edema GT-positive/T2-present 最好 `0.1872` vs baseline `0.3944`。no-T2 edema decode/export sanity 诊断通过，CSV 中 no-T2 edema voxels 为 0。

## Controlled Decisions

| decision | result | note |
| --- | --- | --- |
| committed source can reproduce anchor/component claim | SUPPORTED | forward signature and all runner forwards include anchors/components |
| exact Slurm runtime evidence | PARTIAL | configs/summaries/job status present; raw logs are zero bytes |
| full SRR-v2.5 implementation claim | PARTIAL | core mechanisms present, but prototype/CineMA/registration claims incomplete |
| diagnostic packet integrity | PARTIAL_REPRODUCIBLE | enough for current-packet STOP, not for route promotion |
| validation packaging/upload | BLOCKED | task forbids packaging/upload |
| fold expansion or next-stage training | BLOCKED | not authorized by this forensic review |

## Evidence Files Written

This review created the forensic evidence packet under `results/20260704_anchor_srr_forensic_repro_audit/`:

- `result.md`
- `implementation_claim_truth_table.md`
- `repo_vs_runtime_diff.md`
- `exact_code_used_by_slurm_57782211.md`
- `source_line_evidence.md`
- `uncommitted_required_evidence.md`
- `diagnostic_packet_risk_assessment.md`
- `recommended_next_action.md`
- `MANIFEST.md`

No code, training data, checkpoints, predictions, validation package, upload, commit, or push was performed.

