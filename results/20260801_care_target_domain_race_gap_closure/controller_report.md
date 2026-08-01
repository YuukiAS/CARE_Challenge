此前把任务停在 W0 是错误的资源判断：`61220581 / htzhulab / g1807htzh01` 确实是可复用的 H100 interactive allocation。当前控制器已经撤销旧 blocked 结论，并继续执行同一目标：M3 fold2/fold3 已在 interactive allocation 中完成 4000-step 正式训练；M0R fold2 已在 htzhulab 跑；M0R fold3 的 pending job 已取消并接到 interactive allocation；M1 fold2/fold3 仍在队列等待下一次接力；M2 源码已 pin，但 Google Drive 权重/ViT 资产未落地，所以只能记录 asset gate，不能提交假训练。

# Controller Report

- controller_verification_decision: `ACTIVE_CONTINUATION`
- scientific_decision: `CONTROLLER_ACTIVE_CONTINUATION`
- previous_decision_superseded: `OPERATIONALLY_BLOCKED_EXISTING_INTERACTIVE_LOST`
- task_key: `20260801_care_target_domain_race_gap_closure`
- phase: `PREFLIGHT_AND_SCHEDULING_ACTIVE`

## Practical Meaning

旧 M0 已被重新审计，不能再叫忠实目标域微调负结果。它实际继承 nnU-Net 默认的 SGD、初始学习率 1e-2 和 PolyLR，只是把训练缩到 16 epoch/4000 step，并且没有 500-step checkpoint 的全体积 inner selection。因此它只能作为高学习率短周期微调的负结果。

四条 lane 的当前状态不是“都失败”。M0R 和 M3 已通过 fold2/fold3 preflight，并共享同一批次 manifest hash；M3 两折已完成正式 4000-step patch-head 训练；M1 已改成不使用 T1/T2star placeholder 的 C0/LGE/T2-only CARE adapter，并通过 1-step actual-data GPU smoke；M2 已 pin 到官方源码，但还缺上游 Google Drive weights/ViT asset。

## Evidence

- old M0 audit: `results/20260801_care_target_domain_race_gap_closure/m0_protocol_fidelity_audit.json`
- split copy/hash: `results/20260801_care_target_domain_race_gap_closure/split_receipt_copy.json`
- interactive evidence: `results/20260801_care_target_domain_race_gap_closure/existing_interactive_receipt.json`
- lane preflight: `results/20260801_care_target_domain_race_gap_closure/lane_preflight_summary.json`
- external assets: `results/20260801_care_target_domain_race_gap_closure/external_assets_plan.md`
- scheduler receipt: `results/20260801_care_target_domain_race_gap_closure/scheduler_receipt.json`
- M3 launcher log: `/users/a/e/aereinh/.tmp/codex-CARE/20260801_care_target_domain_race_gap_closure/logs/m3_interactive_61220581_launcher_v2.log`
- validator: `scripts/validation/validate_target_domain_race_gap_closure.py`

## Unauthorized

- no new interactive allocation
- no a100-gpu or volta-gpu submission
- no validation packaging/upload
- no Docker upload
- no hosted metric claim
