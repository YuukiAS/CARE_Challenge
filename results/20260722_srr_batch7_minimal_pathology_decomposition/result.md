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
- formal Slurm training: scar preflight PASS; first formal scar attempt failed before matched BR2 completion and remains zero formal completion evidence
- post-runtime aggregation: implemented; intentionally fails if required variant summaries/eval artifacts are missing

## 验证

- `python -m pytest -q tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> 22 passed
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
- 2026-07-22T00:59:42-0400: htzhulab job `59983573` still `PENDING(Resources)` with scheduler `StartTime=2026-07-22T04:47:41`, about 3h48m after check and close to the 4h job budget. Per routing policy, submitted isolated a100 mirror.
- 2026-07-22T01:00:18-0400: submitted formal scar matched wave a100 mirror job `59983784`, attempt `batch7_minimal_decomposition_scar_a100_formal_20260722_010010`; initial state `PENDING(Priority)`, formal_training_credit=0. Whichever partition starts first must keep running; the other pending mirror must be cancelled before duplicate runtime writes become terminal evidence.
- 2026-07-22T01:02:32-0400: htzhulab formal scar job `59983573` started on `g180702`, elapsed `00:00:43`; log `logs/srr_batch7_minimal_decomposition/B7MinDec_scar_59983573_20260722_010156.log` shows CUDA visible and `scar_minimal` command started. a100 mirror `59983784` was cancelled while still pending. This is running evidence only, not terminal completion or aggregation.
- 2026-07-22T01:16:28-0400: htzhulab formal scar job `59983573` reached terminal `FAILED`, exit code `1:0`, elapsed `00:10:12` on `g180702`. The log shows `scar_minimal` produced step 200/400 outputs, then `scar_br2_warmup50` failed before optimizer credit with `ValueError: Batch7 minimal decomposition forbids formal M10 spatial dictionary use`. This is a same-scope startup defect, not completion evidence; formal_training_credit remains 0 for the failed attempt.
- Same-scope repair applied: Batch7 formal minimal decomposition now passes explicit `batch7_minimal_decomposition_mode` to all minimal/warmup/no-SIP/SIP matched runs, disabling legacy M10 spatial dictionary, prototype-map, and semantic-memory formal assets for the decomposition scope. BR2 now fail-closes unless this mode is enabled. Regression tests prove historical M10 can still instantiate the dictionary outside Batch7 mode, Batch7 minimal and BR2 decomposition both disable it, and BR2 without Batch7 mode is known-bad.
- Repair verification before replacement submission: `python -m pytest -q tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> 23 passed; `python scripts/evaluation/validate_srr_batch7_minimal_decomposition_packet.py --preflight` -> passed; `python scripts/training/run_srr_batch7_minimal_decomposition.py --pathology scar --print-contract` -> exit 0 and printed all four scar contracts with `batch7_minimal_decomposition_mode=true`; `python scripts/srr_production/audit_formal_entrypoints.py --strict` -> failure_count 0.
- 2026-07-22T01:18:34-0400: submitted repaired formal scar replacement htzhulab job `59984573`, attempt `batch7_minimal_decomposition_scar_htzhulab_formal_repair_m10dict_20260722_011818`, source commit `ebbc5aac03e135cd6cddd4e0cec9386cc126ce30`. Initial state is `PENDING(Resources)`, estimated start `2026-07-23T15:45:56`, formal_training_credit=0 until terminal runtime and aggregation.
- 2026-07-22T01:19:23-0400: because the htzhulab replacement start estimate is far longer than the 4h job budget, submitted isolated a100 routing mirror job `59984591`, attempt `batch7_minimal_decomposition_scar_a100_formal_repair_m10dict_20260722_011818`, source commit `ebbc5aac03e135cd6cddd4e0cec9386cc126ce30`. Initial state is `PENDING(Priority)`. If either replacement starts, the other pending mirror must be cancelled before duplicate terminal evidence can be produced.
- 2026-07-22T01:22:43-0400: jobs `59984573` and `59984591` were both found `CANCELLED by 397557` before any Start time, with elapsed `00:00:00` and no allocated node. They have no runtime output and zero formal_training_credit. The source tree is now clean at `de3c3b3cc3a11e14de63f6d49f9fda4d925d701d`; next action is to resubmit the scar replacement from this final Batch7 minimal-decomposition-mode commit.

- 2026-07-22T01:21:53-0400: cancelled stale replacement jobs `59984573` and `59984591` before they started. Reason: they were submitted from commit `ebbc5aac03e135cd6cddd4e0cec9386cc126ce30`, which fixed only the BR2 branch but still allowed `scar_minimal` to instantiate the legacy M10 spatial dictionary; those pending jobs would not satisfy the current six-run formal comparison contract.
