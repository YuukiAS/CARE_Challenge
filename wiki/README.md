# CARE 架构 Wiki

architecture_version: `care-agent-flow-v2-batch5-controller-verified`
latest_verified_milestone: `M9 follow-up evidence reconciliation`
latest_executor_packet: `Batch5 post-Batch4 diagnostic repair`
latest_review_token: `M9_FOLLOWUP_AUDITED_READY_NO_PROMOTION_DIAGNOSTIC_ONLY`
route_status: `M9_NO_PROMOTION_DIAGNOSTIC_ONLY`
code_fingerprint: `srr_propref=c939b0a6;infer_myops=2ebdab1a;batch5_selection=93d2be96;batch5_loss=27760631;batch5_validator=7f9a0b68;batch5_config=6ab9ff3f`

本页是 GPT、Codex controller、mapper、finalizer 和 reviewer 读取当前架构状态的根入口。它只描述当前已提交证据，不授权路线晋级、validation packaging/upload、hosted metric claim、M10 或 scientific stop。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

## 组件摘要

| 分支 | 当前判断 |
| --- | --- |
| MyoPS SRR | 代码中已有 retrieval、proposal、refiner、arbitration 等运行路径，但 M9 follow-up review 仍是 no-promotion diagnostic-only。 |
| nnU-Net anchor | 只能作为 baseline、context、evidence、safety source，不能替代 SRR 路线定义。 |
| Cine | 目前是 local proxy / final-output evidence，不具备 hosted readiness。 |
| Controller flow | 长 Slurm / overnight work 必须使用 controller-supervised continuity、mapper draft/final、FINALIZER_A/B、validator 和独立 reviewer。 |
| 历史版本 | M8/M9 的路线分析已迁移到 [wiki/history/](history/README.md)，current wiki 只展示当前状态。 |

## Batch5 executor packet

Batch5 post-Batch4 diagnostic repair has a controller-verified packet at `results/20260721_srr_batch5_post_batch4_diagnostic_repair/`. It used the Batch4 selected checkpoint SHA `bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6` on the same 44 MyoPS validation cases with optimizer steps `0`.

Evidence now covers formal logits-argmax checkpoint reranking, HD95 and remote-FP eligibility gates, seven same-checkpoint intervention modes, production correction gate casewise fields, GT-aware oracle headroom, real-checkpoint backward-only loss authority, and frozen prototype hashes. Primary Slurm job `59730568` completed on `htzhulab`; A100 mirror `59730666` was cancelled while pending. This is diagnostic-only controller verification, not training authorization or a hosted metric claim.

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [history/README.md](history/README.md)
- [writing_skill_receipt.json](writing_skill_receipt.json)


## M10 candidate snapshot

M10 follow-up has a local controller packet at `results/20260714_srr_v3_m10_continuation_reconciliation/`. It is a `candidate_unreviewed` operational packet, not a new current reviewed milestone. F1 MyoPS reconciliation and F2 Cine fidelity passed their local validators, but F3 Cine temporal runtime is `NEEDS_EVIDENCE` after job `58997393` timed out before terminal temporal outputs. `wiki/current_state.yaml` therefore remains on M09 until independent runtime review and a later reconciliation task.
