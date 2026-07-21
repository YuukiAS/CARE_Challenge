# Batch7 Repair Controller Report

这次执行把 Batch7 的机制闭环从占位证据修成了真实、可复查的模型证据：44例独立验证集干预、语义记忆、anchor-free discovery、严格验证器和600步 proposal 训练都已经跑完。关键科学结果是，proposal 修复只让 edema 略有改善，但 scar 变差，并且 help/harm 和 remote FP 门槛没有通过。因此不能继续训练 refiner、arbiter 或 production gate，也不能扩大到 folds、Cine、上传或 hosted 指标声明。

controller_verification_decision: VERIFIED_COMPLETE

## Decisions

- `B7R_WAVE0`: completed bootstrap and superseded old copied intervention tables.
- `B7R_WAVE1`: completed real intervention infrastructure and fail-closed validator.
- `B7R_WAVE2`: completed real semantic memory, anchor-free discovery, checkpoint roundtrip, and pathology-separated gradient authority.
- `B7R_WAVE3`: completed real 11-mode x 44-case intervention replay. Validator passed after same-wave repair of mode semantics.
- `B7R_WAVE4`: completed 600 proposal optimizer steps and aggregation. Proposal continuation gate failed.
- `B7R_WAVE5`: not run because proposal gate failed.
- `B7R_WAVE6`: not run because proposal gate failed.
- `B7R_WAVE7`: finalized stop packet.

## Proposal Gate

- `actual_optimizer_steps`: 600
- `selected_checkpoint_path`: `results/20260721_srr_batch7_mechanism_closure_repair/runtime/stages/proposal/attempts/batch7_repair_proposal_htzhulab_59828884/variants/batch7_repair_proposal_htzhulab_59828884/checkpoints/fold_0/propref_config/checkpoint_validation_step_600.pt`
- `selected_checkpoint_sha256`: `a2412889d55a0e3eee0ca2d57a77f34db0f10f0a069193cc906785f49fae97f1`
- `mean_positive_dice_delta`: 0.0012229660043303135
- `scar_positive_dice_delta`: -0.0019961365973601626
- `edema_positive_dice_delta`: 0.0044420686060207895
- `help_count`: 25
- `harm_count`: 27
- `observed_remote_fp_relative_worsening_max`: 0.053052516728197975
- `continuation_gate_decision`: `FAIL`

## Slurm Evidence

- Wave2 semantic memory: `59797661`, `COMPLETED`, `0:0`, `00:01:07`, log `logs/srr_batch7_repair/B7RMem_59797661_*.log`.
- Wave2 final implementation check: `59810049`, `COMPLETED`, `0:0`, `00:00:23`, log `logs/srr_batch7_repair/B7RChk_59810049_*.log`.
- Wave3 accepted intervention replay: `59812403`, `COMPLETED`, `0:0`, `00:23:40`, plus targeted `production_gate_one` rerun `59821479`, `COMPLETED`, `0:0`, `00:05:09`.
- Wave4 proposal training attempt: `59828884`, Slurm `FAILED 2:0` as the encoded proposal continuation-gate stop; training reached 600 steps and local deterministic aggregation exited 0.

## Validation

- Command: `./envs/env_CARE/bin/python scripts/evaluation/validate_srr_batch7_repair_packet.py --final --write-status`
- Result: `PASS`
- Known-bad upstream packet: rejected with missing/copy/gradient errors.

No Batch8, monolithic 1200-step run, fold expansion, Cine, validation upload, hosted claim, route promotion, M11, or push was run.
