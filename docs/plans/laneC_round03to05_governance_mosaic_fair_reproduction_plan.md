# MoSAIC fold0 fair reproduction governance plan

Plan metadata:
- Type: governance/execution plan
- Lane: Lane C, external baseline and mechanism screening
- Round scope: round03to05
- Status: active plan
- Parent roadmap: docs/plans/
- Parent plan: docs/plans/laneC_round03to05_governance_portfolio_repo_screening_da_plan.md
- Function: make MoSAIC fold0 baseline comparison visible and auditable before any training or integration
- Do not: train, upload validation, depend on MoSAIC in production paths, or commit MoSAIC checkpoints/predictions

MoSAIC 当前只作为外部 baseline 候选进入公平复现闭环。第一阶段的科学目标不是提高分数，而是证明比较条件一致：同一 fold0 44 例、同一输入通道语义、同一 CARE 几何导出、同一 label 映射、同一 positive-GT population、同一 Dice/exact-HD 实现。若 native MoSAIC 源码不可用，任务必须停在 `NEEDS_MOSAIC_SOURCE`，不能用权重存在来替代 native 复现。

## Repository-visible artifacts

- Baseline note: `docs/notes/baseline/MoSAIC_fair_reproduction.md`
- Asset manifest: `third_party/MoSAIC/weights_manifest.json`
- Protocol config: `configs/baselines/mosaic_fold0_fair.yaml`
- Protocol helpers: `code/MoSAIC/mosaic_fair_protocol.py`
- Inference wrapper: `scripts/inference/run_mosaic_fold0_fair_inference.py`
- Evaluation wrapper: `scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py`
- Slurm entrypoint: `jobs/evaluation/mosaic_fold0_fair.sh`
- Result packet: `results/20260725_care_m0_mosaic_fold0_fair_repro/`

## Guardrails

- `MOSAIC_ROOT` defaults to `/users/a/e/aereinh/MoSAIC`; do not move the cache into the repo.
- `.pt`, `.nii.gz`, prediction trees, checkpoints, and runtime caches remain ignored.
- Old Batch10 production-path restrictions on MoSAIC remain unchanged. This plan creates a separate baseline-comparison task only.
- Native MoSAIC requires native source code or an explicitly validated native entrypoint. Without that, write `NEEDS_MOSAIC_SOURCE`.
- Training, fold expansion, validation upload, hosted metric claims, and production dependency are out of scope.

## Acceptance gate

The first acceptable terminal packet must include `protocol_receipt.json`,
`label_mapping_audit.csv`, `geometry_audit.csv`, `casewise_metrics.csv`,
`metrics.csv`, and `result.md`. It may only say
`VERIFIED_EVALUATION_COMPLETE` when all 44 fold0 cases are evaluated for each
declared model with matching geometry and label semantics. Otherwise it must
name the missing evidence.
