# SRR-v3 Reviewer Prompts

Copy exactly one section into a separate read-only Codex reviewer/auditor session after the corresponding executor result has been committed and pushed by the user. The reviewer must commit locally and stop. The user manually pushes.

## Global reviewer rule

```text
这是独立只读 reviewer/auditor session。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动下一个 milestone。只审阅对应的 results/<task_key>/，最后只写该目录下的 review.md，并给出该 milestone 允许的 controlled decision。写完后用 git add -f 提交 review.md，但不要 push，由用户手动 push。
```

## M0 reviewer

```text
只读审阅 results/20260705_srr_v3_m0_architecture_master_contract/。请读取 prompts/tasks/20260705_srr_v3_m0_architecture_master_contract.md、prompts/MILESTONE_REVIEW_PROTOCOL.md、prompts/HANDOFF_GATE_POLICY.md、prompts/GPT_HARD_GATE_PROMPT.md、handoff hard-gate repair review、SRR-v2.5 evidence supplement audit，以及 M0 result directory。检查 required outputs 是否齐全，completion_check.md 是否为 M0_READY_FOR_REVIEW，architecture/interface/metric/hard-gate/downstream graph 是否 machine-checkable，是否违反 forbidden substitutes，是否错误写了 review.md 或启动 M1。最后只写 results/20260705_srr_v3_m0_architecture_master_contract/review.md，decision 只能是 M0_AUDITED_GO、M0_AUDITED_NEEDS_REVISION 或 M0_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M1 reviewer

```text
只读审阅 results/20260705_srr_v3_m1_runtime_instrumentation_gate/。请读取 prompts/tasks/20260705_srr_v3_m1_runtime_instrumentation_gate.md、M0 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M1 result directory。检查 M1 是否真的导出了 gate open-rate、bounded delta、gate*delta、decode label delta、anchor confidence、prototype T2-present coverage、anchor/component alignment、no-T2 safety；检查 required outputs 和 completion_check.md；确认没有训练新模型、没有跳到 M2、没有 route promotion。最后只写 results/20260705_srr_v3_m1_runtime_instrumentation_gate/review.md，decision 只能是 M1_AUDITED_GO、M1_AUDITED_NEEDS_REVISION 或 M1_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M2 reviewer

```text
只读审阅 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/。请读取 prompts/tasks/20260705_srr_v3_m2_myops_bounded_runtime_repair.md、M1 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M2 result directory。检查 closed-gate identity、correction-positive gate opening sanity、strong encoder/context sanity、T2-present edema prototype coverage、proposal/refinement bounded local ROI evidence、no-T2 end-to-end safety、cache/provenance isolation、unit tests 和 required outputs。确认没有 full-fold training、没有 validation package/upload、没有 route promotion、没有启动 M3。最后只写 results/20260705_srr_v3_m2_myops_bounded_runtime_repair/review.md，decision 只能是 M2_AUDITED_GO、M2_AUDITED_NEEDS_REVISION 或 M2_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M3 reviewer

```text
只读审阅 results/20260705_srr_v3_m3_myops_min_effective_pilot_training/。请读取 prompts/tasks/20260705_srr_v3_m3_myops_min_effective_pilot_training.md、M2 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M3 result directory。检查 minimum_effective_training 是否满足：至少 1200 optimizer steps、1800 秒 train loop、至少 12 个 eval cases、one-batch overfit、prediction sanity、loss decrease、same-split nnU-Net baseline、cache isolation。检查 training curves、validation events、prediction sanity、gate/residual stats、prototype bank summary、same-split help/harm、hard subgroup metrics、adequacy_check 和 required outputs。确认它不是 6-step smoke、不是 eval-only over old checkpoint、不是 full-fold route promotion。最后只写 results/20260705_srr_v3_m3_myops_min_effective_pilot_training/review.md，decision 只能是 M3_AUDITED_GO、M3_AUDITED_NEEDS_REVISION 或 M3_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M4 reviewer

```text
只读审阅 results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/。请读取 prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md、M3 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M4 result directory。检查 ablation matrix 是否覆盖 closed gate、no anchor、residual frozen、dictionary/prototypes、semantic retrieval、component proposal、anatomy ROI、local refinement 等机制；每行是否有 same-split help/harm、gate/residual、prototype/dictionary、proposal/refinement、hard subgroup 和 provenance。确认没有把 undertrained smoke 当成机制结论，没有 route promotion，没有启动后续 MyoPS milestone。最后只写 results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness/review.md，decision 只能是 M4_AUDITED_GO、M4_AUDITED_NEEDS_REVISION 或 M4_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M5 reviewer

```text
只读审阅 results/20260705_srr_v3_m5_cine_secondary_contract/。请读取 prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md、M0 review、milestone review protocol、handoff gate policy、GPT hard-gate prompt，以及 M5 result directory。检查 CineMA/anatomy prior、ANTsPy SyN same-safe-subset matrix、VoxelMorph status、frame0/ED controls、temporal dictionary readiness、frame-quality/motion-saliency router、missing evidence 和 required outputs。确认没有把 frame0-only、one-case SyN smoke 或 untrained VoxelMorph adapter 冒充 full temporal retrieval，没有 hosted Cine metric claim，没有 validation package/upload。最后只写 results/20260705_srr_v3_m5_cine_secondary_contract/review.md，decision 只能是 M5_AUDITED_DIAGNOSTIC_GO、M5_AUDITED_NEEDS_REVISION 或 M5_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M6 reviewer: MyoPS co-equal SRR/segmentation decode-refiner repair

```text
只读审阅 results/20260705_srr_v3_m6_myops_coequal_decode_refiner_repair/。请读取 prompts/shared/EXECUTOR_PROMPTS.md 中的 M6 executor、prompts/MILESTONE_REVIEW_PROTOCOL.md、prompts/HANDOFF_GATE_POLICY.md、prompts/GPT_HARD_GATE_PROMPT.md、M4 review，以及 M6 result directory。不要补 executor 缺失文件，不要修改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M7。

重点检查 M6 是否真正按 M4 结论修复 MyoPS 主线，而不是把 SRR 降级成 nnU-Net 的可有可无后处理。必须审阅：

1. coequal_repair_contract.md 是否明确把分割模型分支和 SRR 分支写成同级候选，并说明 closed-gate fallback 只是安全刹车，不是目标路线。
2. branch_arbitration_sanity.csv 是否导出 anchor_weight、srr_weight、refiner_weight、chosen_source 或等价字段，并证明 SRR 在 correction-positive sanity 中能被采用，分割分支在 SRR 低质时也能被采用。
3. decode_gate_consistency_sanity.csv 是否证明 gate/refiner mask 关闭或仲裁选择分割分支时 final labels 精确等于分割分支；不能允许 hidden decode delta。
4. loss_refiner_component_sanity.csv 是否有非空 loss component 数值、梯度或 one-step update sanity，覆盖 SRR 分支监督、分割分支保持、仲裁一致性、bounded correction、component/remote-FP、no-T2 edema 和 local refiner ROI 项。
5. refiner_roi_component_sanity.csv 是否证明 local refiner 是 bounded crop/local correction，不是 full-volume residual，并导出 scar/edema crop ratio、residual magnitude、component/remote-FP proxy。
6. no_t2_safety_sanity.csv 是否证明 no-T2 edema 在 proposal、loss、refiner、final decode、export 上全链路安全。
7. strict_validator_report.md 和 unit_test_report.md 是否 fail closed 于 claim-only、hidden-decode-delta、SRR-zero-contribution、no-T2 unsafe、full-volume-refiner 等 known-bad cases。
8. required outputs、completion_check.md、review_request.md、MANIFEST.md 和必要 first-party helper/source/config 是否已 git-tracked；是否没有提交 checkpoints、NIfTI predictions、upload packages、大日志、raw data、secrets 或整个 runtime tree。

如果 SRR contribution 在所有 correction-positive sanity 中为 0，或者 gate/refiner mask 关闭时 final labels 仍改变，或者 loss/refiner 只有自然语言说明没有数值/梯度/one-step evidence，或者 no-T2 edema 不安全，decision 必须是 M6_AUDITED_NEEDS_REVISION 或 M6_AUDITED_NEEDS_EVIDENCE。最后只写 results/20260705_srr_v3_m6_myops_coequal_decode_refiner_repair/review.md，decision 只能是 M6_AUDITED_GO、M6_AUDITED_NEEDS_REVISION 或 M6_AUDITED_NEEDS_EVIDENCE。完成后 git add -f review.md 并 commit；不要 push，由用户手动 push。
```

## M6 reviewer: SRR-v3 diagram-faithful MyoPS repair

Use this version instead of the earlier abstract co-equal M6 reviewer prompt when reviewing M6.

```text
只读审阅 `results/20260705_srr_v3_m6_myops_diagram_faithful_repair/`。请读取本文件的 M6 executor、`prompts/MILESTONE_REVIEW_PROTOCOL.md`、`prompts/HANDOFF_GATE_POLICY.md`、`prompts/GPT_HARD_GATE_PROMPT.md`、M4 review，以及 M6 result directory。不要补 executor 缺失文件，不要改模型代码，不要训练，不要 validation packaging/upload，不要 route promotion，不要启动 M7。

重点检查 M6 是否回到 v2/v2.5/v3 图中的完整 SRR-MyoPS 路线，而不是把 SRR 抽象成普通后处理，也不是把 nnU-Net/分割模型当成唯一主角。必须审阅：

1. `srr_v3_fidelity_contract.md` 与 `architecture_component_trace.csv` 是否逐项覆盖图中模块：inputs/availability、modality-specific stems、strong encoder、segmentation context interface、semantic retrieval bank、shared/private/interaction dictionaries、real train/OOF prototypes、anatomy decoder、scar/edema proposal、soft-ROI refinement、training objectives。
2. `segmentation_context_interface_sanity.csv` 是否证明 nnU-Net/强分割模型以 logits/probabilities/hard prediction/components/uncertainty/anatomy context 进入 proposal/refiner/arbitration，而不是绕过 SRR 直接成为最终答案。
3. `retrieval_bank_runtime_sanity.csv` 是否证明 retrieval bank、router、dictionary slot usage、prototype source、anatomy/scar/edema routed features 在 runtime 中非空、可追踪。
4. `anatomy_proposal_sanity.csv` 是否证明 `P_union/P_LV/P_RV`、anatomy prior/distance/uncertainty gate、scar/edema proposal decoder 都产生有效证据。
5. `branch_arbitration_sanity.csv` 是否导出 segmentation_weight、srr_retrieval_weight、proposal_weight、refiner_weight、chosen_source 或等价字段，并证明 SRR 在 correction-positive sanity 中能被采用，分割分支在 SRR 证据低质时也能被采用。
6. `decode_gate_consistency_sanity.csv` 是否证明 explicit fallback、gate/refiner mask 关闭或仲裁选择纯分割分支时 final labels 精确等于分割分支；不能允许 hidden decode delta。
7. `loss_refiner_component_sanity.csv` 是否有非空 loss component 数值、梯度或 one-step update sanity，覆盖 SRR retrieval/proposal/refiner、分割分支保持、仲裁一致性、bounded correction、component/remote-FP、no-T2 edema、local refiner ROI、dictionary/prototype regularization。
8. `refiner_roi_component_sanity.csv` 是否证明 local refiner 是 bounded soft-ROI correction，不是 full-volume residual，并导出 scar/edema crop ratio、residual magnitude、proposal recall/precision proxy、component/remote-FP proxy。
9. `no_t2_safety_sanity.csv` 是否证明 no-T2 edema 在 proposal、loss、refiner、final decode、export 上全链路安全，且 no-T2 myocardium 没有被当作 edema negative。
10. `strict_validator_report.md` 和 `unit_test_report.md` 是否 fail closed 于 claim-only、missing architecture trace、hidden-decode-delta、SRR-zero-contribution、loss-components-empty、no-T2 unsafe、full-volume-refiner 等 known-bad cases。

如果图中关键模块没有 runtime evidence，或者 SRR retrieval/proposal/refiner 全为空，或者 segmentation context 绕过 SRR 直接成为最终输出，或者 gate/refiner mask 关闭时 final labels 仍改变，或者 loss/refiner 只有自然语言说明没有数值/梯度/one-step evidence，或者 no-T2 edema 不安全，decision 必须是 `M6_AUDITED_NEEDS_REVISION` 或 `M6_AUDITED_NEEDS_EVIDENCE`。最后只写 `results/20260705_srr_v3_m6_myops_diagram_faithful_repair/review.md`，decision 只能是 `M6_AUDITED_GO`、`M6_AUDITED_NEEDS_REVISION` 或 `M6_AUDITED_NEEDS_EVIDENCE`。完成后 `git add -f review.md` 并 commit；不要 push，由用户手动 push。
```
