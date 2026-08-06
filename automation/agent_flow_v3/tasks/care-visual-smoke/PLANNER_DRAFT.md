# CARE visual smoke — Planner draft

## Binding

```text
task_id: care-visual-smoke
request_nonce: visual-smoke-20260806T031345Z
frozen_contract_sha256: 279550638c5b9940567211ea5e05560048acd0150c6f1ac07ede6a258f139afe
planner_visual_receipt: results/agent_flow_v3/care-visual-smoke/planner_visual_receipt.json
planner_visual_receipt_commit: 182dc161fc3c6d39495e2e192c8c8f9137702bba
planner_decision: VISUAL_SMOKE_PLANNER_PASS
```

本任务只验证 Scheduled GPT 是否能够真实读取三张架构图并把独立观察写回 GitHub。它不授权启动 Controller、Verifier、Executor，不授权 CARE-ASE 实现、训练、outer、Docker、上传、组织方邮件或 `develop -> main` 合并。

## Planner 独立视觉判断

### CARE-ASE

CARE-ASE 是一套保留成熟全体积编码器、瓶颈和共享低中层解码能力的单骨干系统，而不是在 nnU-Net 后面附加一个小修正器。高分辨率阶段将解剖、瘢痕和纯水肿的职责拆开：瘢痕主要由 LGE 定位并重建，纯水肿主要由 T2 驱动，C0 与其他模态只提供受限支持。最终再进行条件类别竞争并保持部署端全体积语义。

图中最关键的安全边界是 no-T2 行为：T2 缺失时，水肿专属计算图不应执行，class 4 不应继续参加六类竞争；最终应当是背景、解剖与瘢痕组成的五类竞争。图中没有 Transformer、Mamba、第二套完整 U-Net、prototype dictionary、SRR retrieval memory、nnU-Net anchor residual arbitration 或 Cine temporal 分支。

### SRR-v3

SRR-v3 的核心不是直接重建整幅病灶，而是围绕成熟 nnU-Net 锚点选择证据并进行有界修正。可观测模态先进入模态特异编码和 availability-aware routing，再形成 shared/private/interaction representation；这些表示与 nnU-Net 的 anatomy、anchor probability、uncertainty、component evidence 以及 positive/negative/safe-negative prototype evidence结合，分别生成 scar 与 edema proposal。随后两个病种进入不同的 soft-ROI refiner，并通过 bounded residual gate 写回最终输出。

缺失模态对应的 private/interaction slot 必须被屏蔽；no-T2 病例不能作为水肿阴性监督，水肿分支应在证据不足时 fail closed。图中还包含独立的 CineMA、registration 和 temporal retrieval 路径。图中没有让新分支无约束地取代整个成熟解码器，也没有单一通用 scar/edema head、Transformer、Mamba 或 center-ID inference。

### MoSAIC

MoSAIC 把 Multi-sequence MyoPS 和 CineMyoPS 组织成两套粗到细流程。MyoPS 侧使用 heterogeneous evidence、CoarseNet、anatomy-conditioned fusion 和独立 pathology experts/FinePathNet 形成瘢痕与水肿区域；Cine 侧以 ED/reference frame 为锚点，结合 anatomy 与 motion evidence 完成多帧推断。

图中没有 SRR 的 shared/private/interaction dictionary、prototype-memory intervention 或 nnU-Net anchor-bounded correction，也没有 CARE-ASE 那种逐行 no-T2 五类竞争合同。因此 MoSAIC 可以作为公开 benchmark 和机制对照，但不能替代 CARE-ASE 的实现合同。

## 三者的结构差异

1. CARE-ASE 的主体是一个 stock-compatible 单骨干全体积重建系统，scar 和 pure-edema 拥有不对称但直接的高分辨率重建责任。
2. SRR-v3 的主体是围绕强锚点的证据选择、proposal、soft-ROI refinement 与有界修正链；其主要风险是模块存在却没有真实进入 final logits。
3. MoSAIC 是 coarse-to-fine 多网络与独立病理专家体系，并另有 ED-anchored Cine 路径；它不使用 SRR dictionary，也不依赖 anchor residual correction。
4. no-T2 安全规则在 CARE-ASE 中最明确：按行排除水肿图并改为五类竞争；SRR-v3 通过 availability、可靠标签和 fail-closed correction表达；MoSAIC 图中没有同等明确的逐行合同。

## Critic 必须独立完成的检查

Critic 不得把本文件或 Planner receipt 当作视觉输入的替代品。Critic必须重新视觉读取同一 nonce 绑定的三张图，并独立判断：

- 上述模块和数据流是否确实可从图中观察到；
- Planner 是否把文字合同中的内容错误投射到了图中；
- no-T2、缺模态和 final-output authority 的解释是否准确；
- “图中明确不存在的组件”是否有误；
- 三者的结构差异是否足以支撑后续 CARE-ASE fidelity review。

Critic 只有在独立视觉 receipt 完整、图片 SHA/nonce 匹配且无未解决歧义时，才能冻结本 visual smoke。若视觉访问失败，应写 `BLOCKED_VISUAL_SOURCES`；若 Planner 观察有实质错误，应直接修订 visual contract/receipt 后重新审计，不得启动任何 Codex 实现角色。
