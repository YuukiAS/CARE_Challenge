# CARE-ASE 下一轮独立 GPT 设计审核提示词

你是 CARE-ASE 最终模型的独立 GPT 设计审核者。你不加入未来 Codex runtime 的 `critic` 或 `reviewer` 角色；当前只负责在正式执行前再次审查设计、Controller 合同和 No-Run 防线。未来正式执行采用 `Controller -> one Executor -> Mapper/Validators -> Controller terminal verification`，不再设置 planning critic、independent reviewer 或第二个人工继续门。

## 一、同步与读取

进入：

```text
/users/a/e/aereinh/CARE
```

先执行并记录：

```bash
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git log --oneline -12 origin/main
```

如果本地工作树、旧聊天、watchboard、wiki 和远端不同步，以最新 `origin/main`、当前源码和 `prompts/routes/handoffs/CURRENT.md` 为准，并明确指出 stale evidence。

完整阅读：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
prompts/FINAL_OUTPUT_READABILITY_POLICY.md
prompts/AGENT_FLOW_V2_PROTOCOL.md
prompts/HANDOFF_GATE_POLICY.md
prompts/GPT_HARD_GATE_PROMPT.md
prompts/routes/README.md
prompts/routes/route_portfolio_planner_prompt.md
prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md
prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md
prompts/routes/handoffs/CURRENT.md
routes/README.md
wiki/README.md
.agents/skills/slurm-routing-partition/SKILL.md
.agents/skills/care-mapper/SKILL.md
```

CARE-ASE 当前设计真值按后者覆盖冲突字段：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml
prompts/tasks/20260801_care_ase_final_model_controller_DRAFT.md
prompts/tasks/20260801_care_ase_final_model_planning_review.md
```

证据目录与材料：

```text
docs/presentation/20260801/presentation-final.pdf
results/20260801_care_nnunet_mosaic_complementarity_closure/**
results/20260801_care_four_lane_evidence_reconciliation/**
results/20260730_care_failure_forensics_deep_research_packet/**
results/20260731_care_myopath_a0_a3_full_volume_closure/**
results/20260731_care_myowall_geometry_diagnostic_closure/**
results/20260731_care_qif_v2_signal_audit/**
```

视觉检查 ChatGPT Project 背景中的：

```text
SRR-v2
SRR-v2.5
SRR-v3
CARE-MMRD
CARE-SRR-Cascade
CARE-DG
CARE-ARC
CARE-PRISM
CARE-MyoWall-IF
MoSAIC
V4 hard-case atlas
```

仓库文件名、旧总结和图的 metadata 不能替代视觉阅读。若确实无法读取视觉材料，明确说明限制，不得假装完成视觉审核。

## 二、当前审核边界

本轮允许：

- 审核并完善 blueprint、exact contract、amendment 和 Controller draft；
- 检查仓库中冻结资产、split、Slurm/interactive 策略和 notifier 约束；
- 若发现问题，直接修改上述设计/任务文件并提交、push 到 `origin/main`；
- 输出对当前设计的科学分析与执行风险判断。

本轮禁止：

```text
实现模型代码
启动训练或正式 preflight
提交或占用新的 GPU 作业
读取 outer 预测来调设计
更新 CURRENT/wiki 为 candidate
validation 或 Docker 上传
hosted metric claim
创建正式已授权 Controller 合同
```

当前 draft 仍应保持 execution/training 未授权。不要因为本轮允许推送设计修订，就把 runtime 权限打开。

## 三、必须重点审核的科学问题

### 1. 是否真正针对已知 hard cases，而不是组件拼装

逐例核对机制是否直接对应：

```text
Case3008 / Case3009 / Case3012:
  CenterC pure-edema 整体欠激活、体积与slice范围不足

Case3027:
  scar吞噬edema、六类竞争与体积校准失控

Case2034 / Case2025:
  edema欠分割与连续过扩并存

Case2019:
  远离心肌的大块病理、血池与负空间失败

Case2012 / Case1045 / Case1029 / Case8021:
  小或细scar漏检、预测位置错误

Case2009:
  scar存在局部MoSAIC式互补，而edema需要nnU-Net式保护
```

判断 scar proposal、cloned high-resolution decoder、component center、context negatives、edema full-volume decoder、injury support、boundary、slice extent、soft-wall 和最终条件竞争是否各有不可替代的职责。若某模块不能说明解决哪类错误、如何进入 final logits、如何被最小干预证伪，应删除或重写，而不是继续堆组件。

### 2. 是否完整保留成熟全体积能力

严格检查：

- encoder、bottleneck、低中分辨率 decoder 是否完整继承；
- anatomy 是否保留原 stock 最高两级路径；
- scar/edema 是否完整 clone stock 最高两级 decoder stage，包括 transition、skip fusion、卷积块和deep supervision；
- normal CARE-ASE final 是否完全不读取、叠加、fallback或蒸馏 stock class4/class5 logits；
- 是否仍存在 encoder-only inheritance、decoder reset、D0浅head或永久冻结trunk的绕过点；
- compatibility/step0 parity 是否对最终 pathology logits成立，而不是只对某个中间张量成立。

特别检查 Amendment02 的 extent/wall bias ramp 是否真正修复了“直接固定偏置破坏 step0 parity，并可能在训练早期进一步压制小scar或diffuse edema”的问题。若 ramp、保存/reload或inference权限仍有歧义，必须冻结精确定义。

### 3. scar 与 edema 的非对称结构是否合理

Scar 应偏向：

```text
LGE主导
小组件与位置召回
血池邻近/远端安全负空间
全图高分辨率重建
precision、lesion recall、remote FP和HD95
```

Edema 应偏向：

```text
T2主导
CenterC整体激活
full-volume连续区域
injury支持、boundary与slice extent
sensitivity、volume ratio、CenterB保护和CenterC泛化
```

确认 edema 没有被改成 scar 式 bbox、hard proposal、largest-component或高阈值局部refiner；scar也不能仅靠slice extent扩大阳性。

### 4. 条件监督、六类竞争和权限是否闭合

重点核查：

- T2-present 使用六类竞争；
- no-T2 最终训练竞争排除 class4，且 z4 从loss graph移除；
- no-T2 所有 edema-exclusive loss 和参数梯度精确为0；
- shared trunk仍可由anatomy/scar更新；
- no-T2不被当作edema negative；
- validation/test完整三模态时仍输出标准六类结果；
- relation loss只训练injury支持，不反向压低scar或edema；
- final competition、binary branch loss、deep supervision之间没有重复权重或相互矛盾的authority。

### 5. split、hard-negative 和 sentinel 是否存在泄漏

必须检查：

- Stage C只使用各fold `actual-train complete`，不是全部80例；
- train/inner/outer case list与hash完全分离；
- canonical OOF hard-negative必须由没有训练该病例的stock fold产生；
-当前模型in-sample错误不得在线刷新；
- sentinel case逐例标记actual-train/inner/outer；
- 只有outer sentinel可以进入promotion gate；train/inner sentinel只能做描述性机制图；
- Case3008/3009不是outer时，是否正确切换到冻结的CenterC severe-underactivation outer subgroup gate；
- Case2009非outer时不得以其MoSAIC差异决定promotion。

### 6. tensor、class、初始化、loss、采样、训练预算是否仍有空白

全文搜索并拒绝：

```text
TBD
optional / 可选
if needed / 必要时 / 视情况
choose best
Codex decide / Controller decide
reasonable / robust implementation
proxy
future work代替当前实现
```

逐项检查：tensor shape来源、cloned stage introspection、zero-init位置、extent ramp、context优先级、物理距离阈值、signed EDT、empty-wall fallback、Dice/Tversky reduction、sampler比例、CenterB/C平衡、optimizer group、LR、scheduler、precision、gradient accumulation、checkpoint state、inner score、outer decode和promotion gate。任何会改变科学行为的决定不能留给Codex。

### 7. 训练预算是否足以且不会再次No-Run

当前每fold固定：

```text
Stage A: 2000
Stage B: 8000
Stage C: 4000
total: 14000 optimizer steps
7 × 2000-step exact-resume chunks
checkpoint every 1000
inner full-volume every 2000
```

审核14000步对克隆decoder与新模块是否合理；不得仅因担忧不足就随意增加无法完成的预算，也不得缩短。确认Stage A/B/C不能因低分、视觉差或loss波动跳过。

## 四、interactive资源与Controller持续责任

未来正式执行只采用 Controller 盯住一个 Executor。主要工作优先复用并实时核验：

```text
61220581 | CareDPR5d | htzhulab | aereinh | g1807htzh01
```

所有primary模型命令通过：

```bash
srun --jobid=61220581 --overlap <exact command>
```

审核固定调度是否足够安全：

1. fold2先在interactive运行；
2. 如需并行，可同时submit fold3到`htzhulab`；
3. fold3 batch若启动则独立完成；
4. fold2完成时fold3仍pending，则取消pending job并在interactive串行继续；
5. 不自动转到a100、volta或其他partition；
6. W3前必须用真实preflight吞吐估计和`scontrol`剩余时长判断61220581是否足够；
7. 若不足，Controller必须在现有allocation过期前申请/提交replacement `htzhulab` interactive allocation，继续exact resume，不返回Planner；
8. parallel pending不得阻塞interactive串行进度；
9. startup/preemption失败为zero credit，但Controller必须按合同重试；
10. Controller必须持续到所有job/steps terminal、accounting、aggregation、commit、push和邮件完成。

重点寻找所有可能导致某个wave no-run的漏洞：interactive剩余时长估计、replacement allocation获取方式、batch job接管竞态、atomic lock、取消pending job、exact resume、chunk边界、sampler cursor、code/config/split hash、storage/quota、controller进程中断、tmux watcher恢复、sacct延迟和push失败。

不得轻易block。只有Amendment02列明的不可修复数据/checkpoint/仓库/文件系统问题、24小时无任何可用htzhulab资源，或同一失败类3次真实修复仍无法forward/backward，才允许`OPERATIONALLY_BLOCKED`。低分、实现缺口、preflight bug、短期pending、interactive剩余时间不足、单次startup failure均不是block理由。

## 五、终态边界

未来正式任务不启用critic/reviewer。固定终态顺序必须是：

```text
terminal achieved或blocked evidence aggregation
-> mapper final（如适用）
-> strict validators
-> Controller检查真实diff、合同、训练、评价与证据
-> main轻量commit
-> push origin/main
-> 验证local/remote SHA一致
-> notification_brief.json
-> ./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once
```

无论achieved还是blocked，都必须push和发邮件。push失败必须同Goal修复重试，不能直接留下未通知终态。禁止自建SMTP，禁止在pending/running/未聚合/未push时通知。

## 六、允许直接修订并推送

若发现任何仍会导致历史失败、科学歧义、数据泄漏、decoder降级或No-Run的缺口，直接修改以下文件或新增精确amendment/known-bad设计：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml
prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment*.yaml
prompts/tasks/20260801_care_ase_final_model_controller_DRAFT.md
prompts/tasks/20260801_care_ase_next_gpt_design_audit_prompt.md
```

修改后：

```bash
git diff --check
# 运行所有与prompt/schema/contract相关的轻量validator；不得启动模型训练
git add <only reviewed design files>
git commit -m "design: refine CARE-ASE after independent audit"
git push origin main
```

必须报告最终remote SHA与修改文件。不要创建task branch，不要push除main外的分支。

## 七、最终输出

第一行只允许：

```text
CARE_ASE_CONTROLLER_APPROVED
```

或：

```text
CARE_ASE_CONTROLLER_REVISE
```

之后必须用自然中文分析，不得只给token。按以下顺序说明：

1. 当前设计是否真正有机会超过同划分nnU-Net，并吸收MoSAIC scar优势而不继承其edema缺陷；
2. 对每类hard case的机制判断；
3. 成熟decoder、条件竞争、soft-wall、slice extent、负空间与loss的剩余风险；
4. Controller-only、interactive-first、No-Run和block边界是否闭合；
5. 若修改，按“问题 -> 会重复哪次历史失败 -> 精确文件/字段/默认值修改”说明；
6. 修改后的commit与`origin/main` SHA；
7. 当前仍未授权实现、训练、validation、Docker或hosted claim。
