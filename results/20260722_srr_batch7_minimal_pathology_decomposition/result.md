# Result 20260722_srr_batch7_minimal_pathology_decomposition

status: partial_complete
self_assessed_status: NEEDS_CONTINUED_EXECUTION

## 执行摘要

当前代码已补上 Batch7 minimal decomposition 的关键 runtime 缺口：现有 MyoPS runner 支持 true resume，恢复 optimizer/RNG 并从 checkpoint global_step+1 继续；Batch7 BR2 schedule 会按 global step 执行 1-50 coefficient/head warmup、51-350 coefficient 与 representer/pathology block 交替、351-400 coefficient/head calibration。

新增 `scripts/training/run_srr_batch7_minimal_decomposition.py` 作为薄 orchestration driver：同一病种先跑 minimal 400，再跑 BR2 warmup 50，然后 no-SIP 与 SIP 从同一个第50步 checkpoint 分叉到 global step 400。source-balanced sampler resume replay 会重放 1-50 的随机消耗，使分叉后的 step 51+ case/patch 序列可匹配。

SIP 权重仍未通过 train-only center-balanced gradient-ratio calibration；driver 会在 `sip_weight_calibration.csv` 没有病种 PASS 行时 fail closed。正式 scar/edema 六组 400-step Slurm、post-completion aggregation、strict validator、mapper final、wiki/CURRENT 终态更新和本地轻量完成提交尚未完成。本文件不是 completion packet。

## 当前新增运行入口

- `scripts/training/run_srr_batch7_minimal_decomposition.py`
- `jobs/srr_production/run_myops_batch7_minimal_decomposition_htzhulab.sh`
- `jobs/srr_production/run_myops_batch7_minimal_decomposition_a100.sh`

## 当前硬门状态

- source=metadata.center sampler: implemented and unit-tested
- availability as observation set: implemented and unit-tested
- BR2 zero-projection staged gradient: implemented and unit-tested
- no-SIP/SIP step50 shared-state driver: implemented, print-contract reaches SIP calibration gate
- SIP train-only calibration: BLOCKING_PENDING_RUNTIME_TRAIN_ONLY_CENTER_BALANCED_GRADIENT_RATIO
- formal Slurm training: NOT_SUBMITTED

## 验证

- `python -m pytest -q tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> 17 passed
- `python scripts/srr_production/audit_formal_entrypoints.py --strict` -> failure_count 0
- `python scripts/training/run_srr_batch7_minimal_decomposition.py --pathology scar --print-contract` -> nonzero at expected SIP calibration hard gate

## 未完成事项

- Generate PASS SIP calibration rows from real train-only center-balanced gradient-ratio checks.
- Run scar/edema matched Slurm jobs through terminal accounting.
- Aggregate all 44-case metrics at step 200/400 and apply complete-trimodal/worst-center gates.
- Run strict validator/known-bad, mapper final, wiki/CURRENT update, and final local commit.
