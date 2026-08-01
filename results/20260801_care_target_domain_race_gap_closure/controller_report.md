当前不能继续训练，也不能改成新开交互任务：这次合同要求必须复用一个正在运行的 htzhulab 交互式 GPU allocation，但当前 Slurm 里没有这样的 allocation，只有 general 分区的 tunnel jobs。按合同，这不是模型失败，也不是实现失败，而是执行资源前提已经丢失；控制器只能写阻塞包、提交推送并通知，不能偷偷申请新的 interactive allocation，也不能把 M3/M0R/M1/M2 改成无交互资源的训练计划。

# Controller Report

- controller_verification_decision: `OPERATIONALLY_BLOCKED`
- scientific_decision: `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST`
- task_key: `20260801_care_target_domain_race_gap_closure`
- phase: `W0_BOOTSTRAP_AUDIT_FREEZE`

## Practical Meaning

旧 M0 已被重新审计，不能再叫忠实目标域微调负结果。它实际继承 nnU-Net 默认的 SGD、初始学习率 1e-2 和 PolyLR，只是把训练缩到 16 epoch/4000 step，并且没有 500-step checkpoint 的全体积 inner selection。因此它只能作为高学习率短周期微调的负结果。

本 goal 后续本来要实现并训练 M0R、M1、M2、M3，但调度合同的第一前提已经失败：没有可复用的 RUNNING htzhulab interactive allocation。因为合同同时禁止 `salloc` 和新建 interactive allocation，控制器不能继续到 preflight 后训练调度阶段。

## Evidence

- old M0 audit: `results/20260801_care_target_domain_race_gap_closure/m0_protocol_fidelity_audit.json`
- split copy/hash: `results/20260801_care_target_domain_race_gap_closure/split_receipt_copy.json`
- interactive evidence: `results/20260801_care_target_domain_race_gap_closure/existing_interactive_receipt.json`
- validator: `scripts/validation/validate_target_domain_race_gap_closure.py`

## Unauthorized

- no new interactive allocation
- no a100-gpu or volta-gpu submission
- no validation packaging/upload
- no Docker upload
- no hosted metric claim
