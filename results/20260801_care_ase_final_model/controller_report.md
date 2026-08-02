# CARE-ASE Controller Report

review_token: VERIFIED_COMPLETE

这次真正完成的是 CARE-ASE 的 main-only 实现、fold2/fold3 固定 14000 步训练、冻结 checkpoint reload 校验、非阻塞 W4.5 实现快照提交/push、一次性 outer 评价、组件干预聚合、mapper final 和 strict validator。后续只剩本报告所在最终轻量 commit、push、SHA 核验和通知发送。

## Scientific Result

W5 使用冻结 `checkpoint_step14000.pt`，fold2/fold3 各 44 个 outer case，推理合同为 `tiled_sliding_window_average_logits`，decode 为固定 argmax。pooled fold2+fold3 outer:

| class | mean Dice | mean HD95 mm | mean precision | mean sensitivity |
| --- | ---: | ---: | ---: | ---: |
| scar | 0.523500573079597 | 22.899074927837937 | 0.5571567770942838 | 0.5798703810407247 |
| pure-edema | 0.7953093461967583 | 7.083419956210938 | 0.8528355923384122 | 0.7789476082483149 |

同划分 stock nnU-Net 的完整 Dice/HD 没有在本 W5 packet 中重算；因此不能声称 CARE-ASE 同时超过同划分 nnU-Net scar 和 pure-edema。`w5_aggregation_receipt.json` 只保留 frozen hard-negative manifest 作为错误背景，不作 hosted metric claim。

Hard cases 和 CenterB/CenterC 显示：CenterB scar 较强，CenterC scar sensitivity 较高但 volume ratio 偏大；CenterB/CenterC edema 仍低于 all_outer，说明纯水肿在困难中心仍是主要失败面。sentinel outer 的 edema mean Dice 为 0.3564320981932369，不能包装成水肿机制已完全解决。

## Component Evidence

W5 module-off intervention 覆盖 11 个 sentinel/hard outer cases，并在同 checkpoint、同输入、同 sliding-window、同 decode 下记录 final-logit delta、changed labels、Dice、HD95、exact HD、component count、remote FP、blood-pool adjacent FP 和 volume ratio。所有声明的组件组至少在一个选定病例上改变 final output:

```text
scar_proposal=true
scar_center=true
scar_context=true
edema_injury=true
edema_boundary=true
edema_context=true
extent_wall=true
```

没有发现降级成 encoder-only、decoder reset、浅层 D0 head、stock class4/class5 logit fallback、selector/ensemble、hard ROI、threshold search、scar priority 或 per-pathology checkpoint 拼接的证据。no-T2 路径在 W2 中验证 class4 从 final loss graph 排除、edema-exclusive gradient 为 0。

## Runtime Accounting

W3 formal training:

| fold | Slurm step | state | elapsed | terminal step | checkpoint |
| ---: | --- | --- | ---: | ---: | --- |
| 2 | 61220581.152 | COMPLETED 0:0 | 06:39:45 | 14000 | `runtime/fold_2/checkpoint_step14000.pt` |
| 3 | 61220581.153 | COMPLETED 0:0 | 06:36:23 | 14000 | `runtime/fold_3/checkpoint_step14000.pt` |

W4/W5 command steps:

| Slurm step | state | elapsed | role |
| --- | --- | ---: | --- |
| 61220581.156 | COMPLETED 0:0 | 00:00:16 | W4 freeze/reload/outer access audit |
| 61220581.157 | COMPLETED 0:0 | 00:00:29 | fold2 outer once |
| 61220581.158 | COMPLETED 0:0 | 00:00:29 | fold3 outer once |
| 61220581.159 | FAILED 1:0 | 00:01:05 | aggregation receipt JSON tuple-key implementation bug |
| 61220581.160 | COMPLETED 0:0 | 00:01:05 | repaired aggregation rerun |

The allocation holder `61220581` remains RUNNING because it is the reused interactive allocation, not a pending formal CARE-ASE training/evaluation chunk. The formal CARE-ASE srun steps listed above are terminal.

## W4.5 Snapshot

implementation_snapshot_commit_sha: `9517fe1738be5a03bc5d9115dade618ca3bc31b8`

audit_package_sha256: `72a05df1bbc882f63780356a423bdeee74b50d5d98df51de1285d9eeffdf2227`

origin/main after W4.5 push receipt commit: `21bfa5a1fbedffcf972005a7183983d1364b1305`

W4.5 was not a critic/reviewer gate. W5 continued without waiting for GPT/user confirmation.

## Evidence Paths

```text
results/20260801_care_ase_final_model/contract_coverage.json
results/20260801_care_ase_final_model/w2_preflight_receipt.json
results/20260801_care_ase_final_model/split_authority_receipt.json
results/20260801_care_ase_final_model/checkpoint_freeze_receipt.json
results/20260801_care_ase_final_model/full_reload_parity_receipt.json
results/20260801_care_ase_final_model/outer_access_audit_receipt.json
results/20260801_care_ase_final_model/w45_implementation_snapshot/w45_implementation_snapshot_push_receipt.json
results/20260801_care_ase_final_model/outer_eval/fold_2/evaluation_receipt.json
results/20260801_care_ase_final_model/outer_eval/fold_3/evaluation_receipt.json
results/20260801_care_ase_final_model/w5_aggregation_receipt.json
results/20260801_care_ase_final_model/module_intervention_outer.csv
results/20260801_care_ase_final_model/hard_case_atlas.md
results/20260801_care_ase_final_model/mapper_final_receipt.json
```

## Machine Fields

controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: COMPLETE_PENDING_FINAL_COMMIT_PUSH_NOTIFY
scientific_decision: NO_HOSTED_CLAIM_NO_PROMOTION_CLAIM
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: FORMAL_CARE_ASE_STEPS_TERMINAL_ALLOCATION_STILL_RUNNING
aggregation_complete: true
git_commit_decision: PENDING_FINAL_COMMIT
git_push_decision: PENDING_FINAL_PUSH
local_main_sha: PENDING_FINAL_COMMIT
origin_main_sha: PENDING_FINAL_PUSH
notification_status: PENDING_FINAL_NOTIFICATION
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
