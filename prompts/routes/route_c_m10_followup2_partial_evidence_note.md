# Route C: M10 follow-up2 partial evidence note

记录时间：2026-07-15

这份说明用于后续 GPT Planner / Critic 读取 `route_C` 时理解旧 M10 follow-up2 的本地残留状态。它不是完成包，不是 runtime review，也不授权继续旧单一路线执行。

## 结论

旧 M10 follow-up2 有有限价值，应保留为 Route C 的历史 evidence 输入和代码资产，但不能当作完成结果。

有价值的部分：

- 新增 checkpoint replay evaluator 要求 `--evaluate --force`，并会真实加载 checkpoint、加载 `state_dict`、在 44 个病例上跑 fresh inference。
- D0 阶段已产生一批 fresh replay evidence：`18 / 125` recoverable checkpoints 被评估，`checkpoint_replay_ledger.csv` 中记录了 `fresh_checkpoint_reload`、checkpoint SHA、loaded state-dict SHA、44-case 清单、inference call count 和 raw prediction manifest。
- 旧 controller 记录显示 D0 replacement job `59150216` 完成；D1 job `59150234` 在最后一次 monitor 时刚开始运行，后续执行被用户终止。
- 代码中保留了严格 validator 和 intervention fail-closed 逻辑，避免把 placeholder intervention 表格误判为通过。

不能作为完成证据的部分：

- `runtime_manifest.json` 状态是 `FRESH_REPLAY_PARTIAL_NEEDS_CONTRACT_COMPLETION`。
- `selected_checkpoints.json` 仍是 `NEEDS_EVIDENCE`，因为 anchor-relative selector 的 immutable nnU-Net anchor SHA 尚未绑定。
- D2/D3 final-output interventions 未实现；`run_srr_v3_m10_followup2_interventions.py` 明确以 `NEEDS_REVISION_REAL_GRAPH_NODE_INTERVENTION_NOT_IMPLEMENTED` fail closed。
- 没有完成 R1 全 checkpoint replay、D2/D3 interventions、R2 Cine fidelity implementation、R3 formal runtime、aggregation、strict validator、controller packet 或 reviewer。
- 没有训练完成证据，也没有 validation packaging / upload 价值。

## 本地 evidence 位置

这些目录默认被 `.gitignore` 忽略，不应整体提交：

```text
results/20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair/
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/
```

关键轻量文件包括：

```text
results/20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair/controller_context.json
results/20260715_srr_v3_m10_followup2_evidence_and_cine_fidelity_repair/r1_monitor_20260715T0633Z.md
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/runtime_manifest.json
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/checkpoint_inventory.csv
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/checkpoint_replay_ledger.csv
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/checkpoint_raw_output_manifest.csv
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/all_checkpoint_case_metrics.csv
results/20260715_srr_v3_m10_followup2_wave2_evidence_repair/selected_checkpoints.json
```

后续 GPT / Codex 不应要求 GitHub 上存在完整 runtime 目录。需要使用这些旧本地证据时，必须重新验证路径、SHA、checkpoint presence 和当前 branch 兼容性。

## 已保留到仓库的代码资产

```text
jobs/src/run_srr_v3_m10_followup2_checkpoint_replay.sh
jobs/src/run_srr_v3_m10_followup2_interventions.sh
scripts/evaluation/evaluate_srr_v3_m10_followup2_all_checkpoints.py
scripts/evaluation/run_srr_v3_m10_followup2_interventions.py
scripts/evaluation/aggregate_srr_v3_m10_followup2_wave2.py
scripts/evaluation/validate_srr_v3_m10_followup2_wave2.py
```

这些文件只作为 Route C 可复用起点。Route C Planner 必须重新决定是否使用、修复或替换它们；Controller 不得直接把它们的旧输出视为完成。

## Route C 使用规则

1. 可以继承 D0 的 partial fresh replay evidence 作为诊断背景，但不能据此选择最终 checkpoint。
2. 若要继续 replay，必须在当前 route_C worktree 重新运行 preflight，并按 route_C 合同重新绑定 code/config/split/checkpoint/anchor SHA。
3. D2/D3 intervention 必须补成真实 final-output graph-node intervention；当前 fail-closed 脚本不能算实现。
4. 任何 packet 中出现 `NEEDS_MONITOR`、`NEEDS_EVIDENCE`、`NEEDS_REVISION`、`FRESH_REPLAY_PARTIAL_NEEDS_CONTRACT_COMPLETION` 都不能请求 reviewer audited-go。
5. 旧 follow-up2 不应阻塞 Route A 或 Route B；它只服务 Route C 的 evidence/fidelity 账本。
