# 病灶 proposal

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

## 0. 当前总判断

M9 不能直接进入 M10。当前独立 review 是 `M9_AUDITED_NEEDS_REVISION`，原因不是 Slurm 仍在跑，而是 evidence packet 内部不一致：`completion_check.md` 和 `result.md` 声称 `M9_READY_FOR_REVIEW`，但核心 tracked evidence 里仍有 `PENDING_RUNTIME`、`PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`、`PARTIAL_ONE_BATCH_PROTOTYPE_EVIDENCE_FORMAL_TRAINING_RUNNING` 等 stale 状态。这个问题必须通过 M9 follow-up 修复 validator 和证据文件后再决定 M10。

科学方向上，M9 的 no-promotion 是有一定证据的。三个 formal SRR-main candidates 都明显低于 tracked M8 nnU-Net anchor：`m9_srr_main_true_br2_pattern_sip`、`m9_srr_main_lesion_proposal_memory`、`m9_srr_main_t2_edema_recall_focus` 的 mean Dice delta 均为负，HD95 和 remote-FP 也更差。训练也不是 smoke：M9 有三个 formal SRR-main candidate 各自超过 7200 train-loop seconds。但是，这些结果仍不能作为“SRR dictionary 路线失败”的最终科学结论，因为 M9 仍存在一批实现与证据缺陷，尤其是 causal ablation、Pattern-SIP、prototype memory、refiner causal effect、Cine temporal output 的真实性不足。

因此当前状态应写作：

```text
M9 executor scientific direction: NO_PROMOTION_DIAGNOSTIC_ONLY, directionally supported
M9 audited packet state: NEEDS_REVISION
M10 status: BLOCKED_UNTIL_M9_FOLLOWUP_REAUDIT
SRR-v3 route status: NOT_PROMOTED, NOT_SCIENTIFICALLY_DISPROVEN
```

---

### 4.1 ProposalDictionary 仍以 buffer prototypes 为主

`ProposalDictionary` 里的 positive / negative prototypes 仍是 `register_buffer`，不是 `nn.Parameter`。`load_prototype_bank` 只是把 train/OOF fitted bank 拷贝进去。这样做比 deterministic axis fallback 强，但不等于在线可学习 prototype memory。

---

### 6.3 Patch-based training 可能限制 lesion formation

当前训练以 patch sampling 为主，batch size 小，foreground/hard-negative oversampling 虽有设计，但 final full-volume behavior 很容易出现 component explosion / remote FP / HD95 失控。M10 如继续 MyoPS，应考虑：

```text
larger context patch or two-stage proposal crop
full-volume calibration pass
post-hoc threshold calibration per pathology using train/val split only
component-aware decode not based on GT
```

---

## 11. 我建议的 M10 优先级

如果 M9 follow-up 修复后仍然是 no-promotion，我建议 M10 先做 MyoPS 的 `Dictionary-led lesion proposal route`，而不是立即转 Cine。理由：dictionary 是项目核心卖点，M9 虽然 SRR-main dense route 失败，但还没有真正验证“dictionary 作为 lesion proposal engine”的版本。

M10 的最小任务不应该是三条大训练并跑 leaderboard，而应该是一个更干净的机制实验：

```text
M10_dictionary_proposal_engine_mechanism_test
```

包含三组：

```text
control: anchor_only + current M9 SRR-main negative reference
candidate_1: dictionary_proposal_without_anchor_context
candidate_2: dictionary_proposal_with_teacher_context_but_not_anchor_base
candidate_3: dictionary_proposal + pathology-specific refiner
```

每组必须有真实 ablation，不能再用 proxy matrix 冒充 causal effect。
