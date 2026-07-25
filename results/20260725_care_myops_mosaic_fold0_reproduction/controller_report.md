MoSAIC 的 fold0 公平复现已经完成本地同口径评价：新训练的 MoSAIC fold0 模型和同一划分 nnU-Net baseline 都在 44 个验证病例上按相同 evaluator 计算，历史 Batch10、SCR-R1 和 Batch7 只作为可追溯背景，不被冒充为本轮同口径新训练结果。当前不上传 validation、不构建 Docker、不 push；下一步应由 Planner 根据病例互补性和主指标差距决定是否值得继续做方法修复。

## Controller Decision
controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: TERMINAL_LOCAL_AGGREGATED
experiment_adequacy_decision: FOLD0_RANDOM_INIT_PUBLIC_CONFIG_REPRODUCTION
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
training_jobs_terminal_accounted: true
aggregation_complete: true
git_commit_decision: LOCAL_LIGHTWEIGHT_COMMIT_REQUIRED_AFTER_FINALIZER_SACCT
git_push_decision: NOT_AUTHORIZED_NOT_PERFORMED
next_required_action: RETURN_TO_PLANNER

## Key Evidence
- canonical casewise: `results/20260725_care_myops_mosaic_fold0_reproduction/canonical_casewise_metrics.csv`
- model summary: `results/20260725_care_myops_mosaic_fold0_reproduction/canonical_model_summary.csv`
- complementarity: `results/20260725_care_myops_mosaic_fold0_reproduction/pairwise_help_harm.csv`
- historical boundary: `results/20260725_care_myops_mosaic_fold0_reproduction/historical_attempt_summary.csv`
## Post-Finalizer Controller Verification

- Replacement repair: original finalizer `60589658` failed on SimpleITK x/y geometry mismatch; `sitk_write_like` was repaired with reference-shape orientation and replacement finalizer `60607636` completed `0:0`.
- Terminal accounting: `60589655`, `60589656`, `60589657`, `60589658`, and `60607636` are all terminal in `slurm_attempts.csv`; failed finalizer is retained.
- Strict validator: `strict_validator_report.json` is `PASS` after post-finalizer self-accounting.
- Focused tests: `63 passed, 18 warnings` for MoSAIC contract/protocol, Batch10 fair inference, and controller notifier tests.
- Mapper: `prompts/routes/handoffs/CURRENT.md`, `wiki/README.md`, and `wiki/current_state.yaml` updated; `validate_care_architecture_wiki.py --strict` and `generate_care_architecture_wiki.py --check` passed.

