# Result 20260722_srr_batch7_minimal_pathology_decomposition

status: partial_complete
self_assessed_status: NEEDS_CONTINUED_EXECUTION

## 执行摘要

当前代码已补上 Batch7 minimal decomposition 的关键 runtime 缺口：现有 MyoPS runner 支持 true resume，恢复 optimizer/RNG 并从 checkpoint global_step+1 继续；Batch7 BR2 schedule 会按 global step 执行 1-50 coefficient/head warmup、51-350 coefficient 与 representer/pathology block 交替、351-400 coefficient/head calibration。

新增 `scripts/training/run_srr_batch7_minimal_decomposition.py` 作为薄 orchestration driver：同一病种先跑 minimal 400，再跑 BR2 warmup 50，然后 no-SIP 与 SIP 从同一个第50步 checkpoint 分叉到 global step 400。source-balanced sampler resume replay 会重放 1-50 的随机消耗，使分叉后的 step 51+ case/patch 序列可匹配。

SIP 权重校准脚本已补上：正式 driver 会在 BR2 warmup 第50步 checkpoint 后运行 `scripts/evaluation/calibrate_srr_batch7_sip_weight.py`，用 train-only center-balanced backward 的梯度比选择 lambda；如果没有病种 PASS 行，SIP 分支仍 fail closed。正式 scar/edema 六组 400-step Slurm、post-completion aggregation、strict validator、mapper final、wiki/CURRENT 终态更新和尚未完成。本文件不是 completion packet。

## 当前新增运行入口

- `scripts/training/run_srr_batch7_minimal_decomposition.py`
- `jobs/srr_production/run_myops_batch7_minimal_decomposition_htzhulab.sh`
- `jobs/srr_production/run_myops_batch7_minimal_decomposition_a100.sh`
- `scripts/evaluation/calibrate_srr_batch7_sip_weight.py`
- `scripts/evaluation/aggregate_srr_batch7_minimal_decomposition.py`
- `scripts/evaluation/validate_srr_batch7_minimal_decomposition_packet.py`

## 当前硬门状态

- source=metadata.center sampler: implemented and unit-tested
- availability as observation set: implemented and unit-tested
- BR2 zero-projection staged gradient: implemented and unit-tested; `br2_staged_gradient_checks.json` is PASS with initial delta 0, step0 projection gradient >0, and post-projection-step beta/representer gradients >0
- no-SIP/SIP step50 shared-state driver: implemented, print-contract reaches SIP calibration gate
- SIP train-only calibration: implemented as warmup-checkpoint backward script; runtime PASS rows pending Slurm execution
- formal Slurm training: NOT_SUBMITTED
- post-runtime aggregation: implemented; intentionally fails if required variant summaries/eval artifacts are missing

## 验证

- `python -m pytest -q tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> 21 passed
- `python scripts/srr_production/audit_formal_entrypoints.py --strict` -> failure_count 0
- `python scripts/training/run_srr_batch7_minimal_decomposition.py --pathology scar --print-contract` -> exit 0, prints calibration command and all branch contracts
- `python scripts/evaluation/validate_srr_batch7_minimal_decomposition_packet.py --preflight` -> exit 0; final mode intentionally fails until six 400-step runs and aggregation finish

## 未完成事项

- Run warmup-checkpoint SIP calibration on real Slurm/GPU attempts and record PASS rows.
- Run scar/edema matched Slurm jobs through terminal accounting.
- Aggregate all 44-case metrics at step 200/400 and apply complete-trimodal/worst-center gates.
- Run strict validator/known-bad, mapper final, wiki/CURRENT update, and final local commit.

## Slurm monitor state

- 2026-07-22T00:03:34-0400: scar GPU preflight htzhulab job `59977481` remained `PENDING(Resources)` with no node/start time; formal_training_credit=0.
- 2026-07-22T00:03:34-0400: scar GPU preflight a100 mirror job `59979732` remained `PENDING(Priority)` with no node/start time; formal_training_credit=0.
- 2026-07-22T00:18:18-0400: scar GPU preflight htzhulab job `59977481` remains `PENDING(Resources)`, `sacct=PENDING`, elapsed `00:00:00`, no allocated node; formal_training_credit=0.
- 2026-07-22T00:18:18-0400: scar GPU preflight a100 mirror job `59979732` remains `PENDING(Priority)`, `sacct=PENDING`, elapsed `00:00:00`, no allocated node; formal_training_credit=0.
- 2026-07-22T00:48:46-0400: scar GPU preflight htzhulab job `59977481` completed on `g180702` with `sacct=COMPLETED`, exit code `0:0`, elapsed `00:00:14`; log evidence: `logs/srr_batch7_minimal_decomposition/B7MinDec_scar_59977481_20260722_004722.log`, `status=CONTRACT_VALID`, formal_training_credit=0.
- 2026-07-22T00:48:46-0400: scar GPU preflight a100 mirror job `59979732` was cancelled by controller after htzhulab terminal PASS; `sacct=CANCELLED`, no allocated node, formal_training_credit=0.
- Current controller head and `origin/main` are both `2b700d073258c7c88cd483f0ec3e5caa4d0a25ae`.
- At preflight close, no formal 400-step Batch7 training had started; next action was formal scar wave submission, then terminal aggregation before edema submission.
- 2026-07-22T00:56:04-0400: submitted formal scar matched wave htzhulab job `59983573`, attempt `batch7_minimal_decomposition_scar_htzhulab_formal_20260722_005552`; initial state `PENDING(Resources)`, formal_training_credit=0 until terminal runtime and aggregation evidence exist.
