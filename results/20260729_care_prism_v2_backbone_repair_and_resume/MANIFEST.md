当前这版只是给 Planner 验收的中间实现包，不是 CARE-PRISM v2 的最终完成包。它已经修复旧的主干资产合同并跑完 W1 机制门和 W2 400 步真实病例 zero-credit preflight；W3 fold0 6500 步、W4 fold1 clean 训练、W5 聚合和最终 Mapper 还没有执行。

```text
task_key: 20260729_care_prism_v2_backbone_repair_and_resume
packet_status: PARTIAL_HANDOFF_FOR_PLANNER_VALIDATION
created_at_utc: 2026-07-29T15:56:18Z
w1_status: PASS
w2_status: PASS_ZERO_CREDIT
w3_status: NOT_STARTED
w4_status: NOT_STARTED
w5_status: NOT_STARTED
```

Tracked lightweight evidence:

- `adoption_receipt.json`
- `backbone_asset_resolution.json`
- `controller_context.json`
- `init_transplant_report_fold0.json`
- `init_transplant_report_fold1.json`
- `multiscale_usage_report.json`
- `data_pipeline_report.json`
- `loss_and_negative_space_report.json`
- `implementation_intervention_report.json`
- `known_bad_report.json`
- `checkpoint_resume_report.json`
- `implementation_validator_report.json`
- `strict_validator_report.json`
- `w2_training_summary.json`
- `eval_probe/case_metrics.csv`
- `eval_probe/summary.json`
- `planner_handoff_partial.json`

Large runtime checkpoint files under `runtime/` are intentionally not tracked.
