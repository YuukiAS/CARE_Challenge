# CARE 当前模型架构

本页记录当前架构状态，供规划者、mapper 和 reviewer 使用。它不是路线晋级结论。

## 2026-08-02 CARE-ASE final model

CARE-ASE 是当前 main 上已实现并完成 fold2/fold3 outer once 的非对称 pathology 模型。它继承同 fold stock nnU-Net 的 encoder、bottleneck 和低中分辨率 decoder；最高两级 decoder 对 scar 与 pure-edema 分支分别 deep-copy，正常 inference 不读取 stock class4/class5 logits。额外证据只通过 zero-initialized residual projection 进入 final pathology logits，并由 W5 module-off intervention 证明会改变 final logits/final labels。

固定评价合同：每 fold 只使用 `checkpoint_step14000.pt`，不使用 inner checkpoint selection；W4 reload parity final-logit max error 为 `0.0`；W5 outer 使用 `tiled_sliding_window_average_logits` 和固定 argmax decode。pooled fold2+fold3 outer 结果是 scar mean Dice `0.5235`，pure-edema mean Dice `0.7953`。这不是 hosted metric claim，也没有授权 validation 或 Docker 上传。

| 组件 | 当前状态 | 证据 |
| --- | --- | --- |
| `care_ase_stock_inheritance` | implemented/verified | `results/20260801_care_ase_final_model/stock_clone_and_parity_receipt.json` |
| `care_ase_no_t2_safety` | implemented/verified | `results/20260801_care_ase_final_model/w2_preflight_receipt.json` |
| `care_ase_outer_evaluator` | implemented/verified | `results/20260801_care_ase_final_model/outer_eval/fold_2/evaluation_receipt.json`; `results/20260801_care_ase_final_model/outer_eval/fold_3/evaluation_receipt.json` |
| `care_ase_module_intervention` | implemented/verified | `results/20260801_care_ase_final_model/module_intervention_outer.csv` |

目标路线仍是 SRR-v3：availability-aware selective retrieval、semantic representation retrieval bank、anatomy-guided lesion proposal、scar/edema pathology-specific soft-ROI refinement，以及 explicit objectives。`nnU-Net` 只能作为 anchor、context、evidence 或 safety source，不能把 SRR 降级成普通后处理。

M9 follow-up 的证据已经完成一致性修复并通过独立 review，但结论仍是 `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`。这表示当前 formal SRR-main candidates 没有超过 tracked M8 `nnU-Net` anchor；它不等于 SRR 路线被科学证伪。

## 当前问题矩阵

| 组件 | 当前状态 | 最主要问题 | 具体 source/symbol | 证据 | M10 目标 |
| --- | --- | --- | --- | --- | --- |
| `inputs_availability` | implemented/verified | 当前代码使用 LGE,T2,C0 availability 顺序；仍需 M10 继续证明困难子组收益。 | `src/care_myocardium/models/srr_propref.py` / `availability` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` | 证明机制贡献或明确降级为 blocker |
| `modality_stems_encoders` | implemented/verified | 结构存在；当前证据不等于 route promotion。 | `src/care_myocardium/models/srr_propref.py` / `self.encoders` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` | 证明机制贡献或明确降级为 blocker |
| `retrieval_dictionary` | partial/verified | M9 仍显示 dictionary 偏 global，lesion-local 贡献未闭环。 | `src/care_myocardium/models/srr_blocks.py` / `dictionary_slot_config` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_dictionary_fidelity_matrix.csv` | 证明 lesion-local dictionary/router 贡献 |
| `router_pattern_sip` | partial/verified | M10 不能只保留 Pattern-SIP 名称，必须证明优化目标和最终输出贡献。 | `src/care_myocardium/models/srr_blocks.py` / `MultiSlotDictionaryRouter` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_dictionary_slot_group_stability.csv` | 证明 lesion-local dictionary/router 贡献 |
| `prototype_memory` | partial/verified | SafePrototypeMemoryBank 仍需证明进入正式前向闭环。 | `src/care_myocardium/models/srr_propref.py` / `ProposalDictionary` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_prototype_update_ledger.csv` | 证明机制贡献或明确降级为 blocker |
| `anatomy_prior` | partial/verified | 需要 M10 量化对 proposal/refiner 的实际帮助。 | `src/care_myocardium/models/srr_propref.py` / `AnatomyDistanceROIPrior` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` | 证明机制贡献或明确降级为 blocker |
| `scar_proposal` | partial/verified | proposal recall/precision 仍需提高并与 final logits 绑定。 | `src/care_myocardium/models/srr_propref.py` / `scar_dictionary` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_proposal_refiner_recall_precision.csv` | 证明 proposal recall/precision 与 final logits 闭环 |
| `edema_proposal` | partial/verified | T2-present edema hardcases 仍是关键缺口。 | `src/care_myocardium/models/srr_propref.py` / `edema_dictionary` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_proposal_refiner_recall_precision.csv` | 证明 proposal recall/precision 与 final logits 闭环 |
| `scar_refiner` | partial/verified | 需要 scar-specific 因果消融。 | `src/care_myocardium/models/srr_propref.py` / `scar_refiner` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_scar_refiner_roi_stats.csv` | 证明 refiner 因果改变 ROI logits/HD95 |
| `edema_refiner` | partial/verified | 需要 edema-specific recall/HD95 证据。 | `src/care_myocardium/models/srr_propref.py` / `edema_refiner` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_edema_refiner_roi_stats.csv` | 证明 refiner 因果改变 ROI logits/HD95 |
| `no_t2_safety` | implemented/verified | 安全已实现，但不能替代 T2-present edema 性能。 | `src/care_myocardium/models/srr_propref.py` / `canonical_t2_present` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` | 证明机制贡献或明确降级为 blocker |
| `arbitration_final_output` | partial/verified | M9 SRR-main 未超过 anchor；不能包装成 ready。 | `src/care_myocardium/models/srr_propref.py` / `BranchArbitrationGate` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` | 证明机制贡献或明确降级为 blocker |
| `losses` | implemented/verified | wiring bug 修复，但机制优化仍不足。 | `src/care_myocardium/losses/srr_losses.py` / `srr_m6_expanded_total_loss` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_loss_weight_wiring_test_report.md` | 证明机制贡献或明确降级为 blocker |
| `checkpoint_selection` | partial/verified | selection rule 仍需更强 validator。 | `scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py` / `select_metric_checkpoint` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/m9_metric_aligned_checkpoint_selection.csv` | 证明机制贡献或明确降级为 blocker |
| `cine_temporal` | partial/unverified | Cine 必做但不能救 MyoPS；仍无 hosted readiness。 | `scripts/evaluation/aggregate_srr_v3_m9_dictionary_fidelity_packet.py` / `Cine` | `results/20260708_srr_v3_m9_dictionary_fidelity_repair_training/review.md` | 从 local proxy 走向成熟 temporal evidence，不能替代 MyoPS |
| `controller_continuity` | partial/unverified | 需要真实 controller runtime evidence 后才能 verified。 | `prompts/CONTROLLER_TASK_PROTOCOL.md` / `controller_supervised` | `wiki/EXECUTION.md` | 保持只做 operational observability，不做科学判断 |
| `mapper_wiki_observability` | partial/unverified | mapper final 在 reviewer 前运行；review token 由 post-review reconciliation 更新。 | `.agents/skills/care-mapper/SKILL.md` / `care-mapper` | `wiki/README.md` | 保持只做 operational observability，不做科学判断 |


## M10 follow-up candidate mapping

M10 follow-up adds tracked candidate evidence for inherited MyoPS checkpoint selection/interventions and first-party Cine fidelity contracts. The new Cine runtime remains incomplete: adapter/control and registration jobs completed, but `real_syn_control.csv` is still `NEEDS_EVIDENCE_REAL_SYN_NOT_RUN_BY_CURRENT_ENTRYPOINT`, and the temporal dictionary replacement timed out before writing terminal outputs. The candidate rows in `COMPONENTS.csv` are marked `NOT_REVIEWED`; they do not update `wiki/current_state.yaml`.

## Batch6 final objective alignment

Batch6 keeps the existing `SRRProposeRefineMyoPS` MyoPS backbone and repairs objective wiring in place. The production final output remains `anchor_bounded_srr_correction`: nnU-Net anchor logits plus bounded scar and edema corrections. The change is that the final deployed six-class logits now receive direct scar and T2-present edema pathology losses, and the production correction gate receives 13-channel context plus repair/preserve supervision.

Runtime evidence:

| Evidence | Result |
| --- | --- |
| fixed-overfit | PASS, job `59743323`, 60 steps, formal credit 0 |
| formal300 | COMPLETED, job `59744053`, 300 steps, 44-case eval at 100/200/300 |
| step300 gate | FAIL because mean positive-pathology Dice delta `+0.001699358` < `+0.003` |
| selected checkpoint | step300, SHA `729c81e49bf846339ed2f39ef0f2656319befd2b9cfe73268d7cf501e6b40fbd` |
| final interventions | COMPLETED, job `59744941`, six modes |

This verifies a connected mechanism path but leaves the scientific signal below usable; it does not authorize 900, fold expansion, upload, Cine, or Batch7.
