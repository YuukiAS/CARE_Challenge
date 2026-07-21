# CARE 架构 Wiki

architecture_version: `care-srr-batch6-final-objective-alignment-stop300`
latest_verified_milestone: `Batch6 final objective alignment`
latest_executor_packet: `Batch6 formal300 gate-fail stop packet`
latest_review_token: `NOT_REVIEWED_CONTROLLER_VERIFIED`
route_status: `BATCH6_BELOW_USABLE_STOP_AT_300_NO_PROMOTION`
code_fingerprint: `srr_propref=8b98ac43;srr_losses=eaabe101;run_myops=e9f531b0;infer_myops=df3922d7;batch6_formal=8619856a;batch6_validator=635f0157;batch6_config=9922ba2c`

本页是 GPT、Codex controller、mapper、finalizer 和 reviewer 读取当前架构状态的根入口。它只描述当前已提交证据，不授权路线晋级、validation packaging/upload、hosted metric claim、fold expansion、Cine、Batch7 或 scientific stop。

## 当前图

![当前模型](figures/model-current.png)

![当前差距](figures/model-gap.png)

![执行流程](figures/execution-flow.png)

## 组件摘要

| 分支 | 当前判断 |
| --- | --- |
| MyoPS SRR | Batch6 修通 direct final logits loss 和 13-channel production gate repair path，fixed-overfit PASS；formal300 mean Dice delta 未达继续门。 |
| nnU-Net anchor | 仍只作为 baseline、anchor、context、evidence 和 safety source，不能替代 SRR。 |
| Cine | Batch6 未授权、未修改、未训练。 |
| Controller flow | 当前为 controller-supervised local packet；executor tmux 只作为执行容器，controller 在主线程完成验收。 |
| 历史版本 | M8/M9/M10 和 Batch5 的历史证据保留在 result packets 与 [wiki/history/](history/README.md)。 |

## Batch6 controller packet

Batch6 final-objective alignment packet is at `results/20260721_srr_batch6_final_objective_alignment/`. It used the Batch4 selected checkpoint SHA `bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6`, passed the required two-case fixed-overfit in job `59743323`, ran formal300 in job `59744053`, and ran final interventions in job `59744941`.

Step300 positive-pathology Dice deltas were edema `+0.002724749` and scar `+0.000673968`; mean `+0.001699358` failed the required `+0.003` continuation gate. Therefore 900-step extension was skipped by contract. This is an operational mechanism-repair completion with below-usable signal, not a performance claim over nnU-Net.

## 入口

- [MODEL.md](MODEL.md)
- [EXECUTION.md](EXECUTION.md)
- [COMPONENTS.csv](COMPONENTS.csv)
- [LINEAGE.md](LINEAGE.md)
- [architecture.yaml](architecture.yaml)
- [history/README.md](history/README.md)
- [writing_skill_receipt.json](writing_skill_receipt.json)
