# CARE Route Portfolio Planner Prompt

你是 CARE GPT Planner。当前任务是为 2026-07-15 至 2026-07-27 的 CARE Myocardium 冲刺制定 Route A、Route B、Route C 的完整可执行规划合同。只做规划，不执行代码、不训练、不提交 Slurm、不写 runtime `review.md`、不合并 route 结果、不上传 validation、不启动 M11。

## 0. 必须先同步并读取

请强制同步远端仓库 `YuukiAS/CARE_Challenge` 的 `main`、`route_A`、`route_B`、`route_C`：

```text
main
route_A
route_B
route_C
```

然后读取：

- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/MILESTONE_REVIEW_PROTOCOL.md`（如存在）
- `routes/README.md`
- `routes/route_A/README.md`
- `routes/route_B/README.md`
- `routes/route_C/README.md`
- `configs/routes/partition_routing.yaml`
- `docs/route_watchboard.md`
- `wiki/README.md`

如果这是 controller/reviewer 执行后的回传或下一步决策，而不是初始三路线规划，还必须先读：

```text
prompts/routes/handoffs/CURRENT.md
```

`CURRENT.md` 是当前 portfolio round 的稳定入口；它会指向当前总 planner handoff 和每条 route 的当前 critic handoff。

必须视觉阅读 ChatGPT Project 背景材料中的 SRR 图（v2 及之后版本），并在 planner audit 中写明你读到的结构要点。仓库中的 `images/SRR-v2.png`、`images/SRR-v2.5.png`、`images/SRR-v3.png` 只能作为版本和文件名参考，不替代 Project 背景图视觉阅读。

## 1. 输出位置与分支

不要默认写 `prompts/shared/`。本次三路线规划的输出默认写入 `prompts/routes/`。

请分别在对应远端分支上提交：

### `route_A`

```text
prompts/routes/route_A.md
prompts/routes/route_A_executor_plan.yaml
prompts/routes/route_A_critic_request.md
prompts/routes/route_A_planner_audit.md
```

### `route_B`

```text
prompts/routes/route_B.md
prompts/routes/route_B_executor_plan.yaml
prompts/routes/route_B_critic_request.md
prompts/routes/route_B_planner_audit.md
```

### `route_C`

```text
prompts/routes/route_C.md
prompts/routes/route_C_executor_plan.yaml
prompts/routes/route_C_critic_request.md
prompts/routes/route_C_planner_audit.md
```

如需组合总纲，可在 `main` 或每个 route 分支中写：

```text
prompts/routes/portfolio_reconciliation_plan.md
```

但不要让组合总纲阻塞任一已通过 Critic 的 route 启动。

## 2. 总目标

目标不是再提交一版普通 nnU-Net。仓库已有 nnU-Net validation 结果，重新包装 nnU-Net 没有意义。三条 route 的共同目标是尽快产出至少一条非纯 nnU-Net、有充分本地证据、有真实代码实现、有可审查 packet 的 MyoPS + Cine 候选。

同时必须读取并执行 `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md` 和 `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`，防止过去 M10 / follow-up / follow-up2 以及本轮 Route A/B 暴露出的偷懒，并确保三条 route 的强要求在后续 round 持续生效：

- 用 `NEEDS_EVIDENCE` 表格冒充 intervention。
- 不带 `--evaluate --force` 却声称 checkpoint fresh replay。
- 简化 checkpoint selection 公式，漏掉 anchor-relative、HD95、remote FP。
- 用 dataclass / mock / fake URL / fake hash 冒充 CineMA、registration、temporal 实现。
- freeze receipt 绑定一套文件，正式 wrapper 调用另一套旧入口。
- pretrained 和 random-init 两个 job 调同一个脚本且没有初始化差异。
- registration 继续使用 direct velocity proxy、proxy Jacobian、proxy SyN。
- temporal 没有真实消费 registered anatomy/features/motion/uncertainty。
- validator 只检查文件存在，不检查语义真实性。
- controller 只相信 completion token，不复核 evidence。
- 用 allowed non-ready token 提前结束本应继续执行的 Slurm/monitor/aggregation 阶段。
- 用 12-step / one-batch / local smoke 冒充合同要求的 first bounded train/eval。
- terminal packet 留下互相矛盾的旧 receipt、mapper report 或 controller context。

## 3. 三条 Route 的边界

### Route A：最小工作量、最快 submission candidate

Route A 必须保留 SRR 架构图的核心思想，但可以做压缩实现。它不能退化成普通 nnU-Net 后处理。

必须包含：

- 冻结或保护已有 nnU-Net 基座。
- SRR evidence 输入，至少包括 D2 / retrieval / anatomy / uncertainty 中可真实读取的一部分。
- scar 与 edema 的 pathology-specific proposal。
- scar 与 edema 的 refiner 或 bounded residual/refinement 头。
- residual gate，使 final output 在 safe gate 下可回退为 nnU-Net。
- negative-space / no-T2 safety。
- T2-conditioned edema supervision。
- local 44-case 或 OOF gate。
- 与 nnU-Net 的 voxel/hash 差异检查。

允许暂缓：

- 完整 interaction dictionary 联合训练。
- 完整 PSIP/SIP 重训。
- full learned registration。

Cine 不能放弃。Route A 的 Cine 最小实现应使用 ED/reference frame、少量关键帧、可靠固定 registration 或 ANTs、多帧 temporal aggregation/refiner，并输出 `myocardium_cinemyops` 可打包候选。不得只包装旧单帧输出然后声称 Cine 完成。

Route A 必须有 24-48 小时硬门：如果本地证据不能超过或安全改进现有 nnU-Net/Cine baseline，必须停止或降级为 negative packet，不能继续长训。

### Route B：完整 SRR-v3 架构实现

Route B 目标是证明完整架构不是图上概念，而是真实可运行系统。

MyoPS 必须规划并实现：

- modality-specific stems。
- availability-aware router。
- shared/private/interaction dictionary。
- prototype memory / OOF prototype bank。
- anatomy decoder。
- scar proposal。
- edema proposal。
- soft ROI。
- scar refiner。
- edema refiner。
- bounded nnU-Net residual correction。
- full loss：anatomy、proposal、refiner、residual、negative-space、dictionary、prior、ROI、可选 alignment。
- save/reload/export。

Cine 必须规划并实现：

- CineMA 或替代 anatomy source 的真实加载。
- 多类 anatomy logits、features、uncertainty。
- ED/reference 和关键帧选择。
- registration interface。
- scaling-and-squaring / Jacobian / inverse consistency（如走 learned registration）。
- ANTs/SyN baseline 或 control。
- temporal representation dictionary。
- temporal aggregation/refiner。
- checkpoint/resume/export。

Route B 的硬门：

```text
先补代码
-> 真实病例 forward
-> loss 非零且梯度到目标模块
-> intervention 能改变 final logits / labels
-> checkpoint save/reload 一致
-> implementation freeze
-> 才允许正式训练
```

任何 placeholder、mock-only、claim-only、旧 wrapper bypass，都必须导致 Critic 或 validator fail closed。

### Route C：完整 M10 follow-up2 evidence / Cine fidelity

Route C 是最大工作量路线，继承 M10 follow-up2 的科学要求，但不再阻塞 A/B。

必须规划：

- MyoPS checkpoint fresh replay。
- D2/D3 selected checkpoint real final-output interventions。
- anchor-relative checkpoint selector。
- eligibility gate：no-T2 edema probability、positive-case nonempty rate、prediction-volume ratio、code/config/split/case/label/preprocess/decode/metric hashes、calibration freeze。
- raw output manifest、state-dict SHA、case list、inference call count。
- CineMA pretrained vs random-init control。
- 真实 CineMA provenance、weights、license、features/logits/uncertainty。
- learned registration 或真实 registration repair。
- symmetric velocity、7-step scaling-and-squaring、Jacobian、inverse consistency、完整 registration loss。
- 真实 ANTs SyN。
- case-level gate。
- selected-checkpoint reload。
- temporal cumulative resume。

Route C 可以并行 MyoPS evidence 与 Cine implementation/runtime，但不得降低证据要求。旧 follow-up2 runtime 已终止，不得把旧 submitted/pending/placeholder packet 当作完成。

## 4. 通用 Implementation Gate

每条 route 都必须在正式训练前通过 implementation gate。

MyoPS gate 至少检查：

- LGE-only、LGE+C0、LGE+C0+T2 三种输入模式真实 forward。
- 缺失模态不进入计算图，不是 zero-filled 假可用。
- router 真实读取 availability 和图像特征。
- dictionary / prototype / anatomy / proposal / refiner 真实参与 forward。
- refiner 或 residual gate 真实改变 final logits。
- loss 数值有限、非恒零、梯度到达目标模块。
- no-T2 edema loss 对 no-T2 样本为零或符合合同。
- save/reload 后输出一致。

Cine gate 至少检查：

- 真实多帧输入。
- 真实 anatomy logits/features/uncertainty。
- registration 或 fixed registration/SyN 真正产生 warp。
- temporal 模块真实读取 registered anatomy/features/motion/uncertainty。
- temporal dictionary/refiner 关闭前后 final output 有差异。
- resume step 不重置。
- 输出可映射回 official label 和 submission layout。

## 5. Compute 与 tmux

三条 route 使用独立 worktree：

```text
/users/a/e/aereinh/CARE_worktrees/route_A
/users/a/e/aereinh/CARE_worktrees/route_B
/users/a/e/aereinh/CARE_worktrees/route_C
```

长期 tmux 常驻 4 个，含 watchboard：

```text
care_watchboard
care_route_A
care_route_B
care_route_C
```

每条 route 只保留一个 route-level session；controller、reviewer、monitor 用该 session 内的 window 区分。Reviewer window 只能在对应 route committed packet 后创建或 resume。不要再为 Route A/B/C 额外常驻独立 reviewer session。

Compute policy：

- 优先充分利用 `htzhulab`、`a100-gpu`、`volta-gpu`。
- 有多个独立 ready job 时，优先分配不同 partition。
- 只有单个关键路径 job pending 时，才三路 race。
- raced jobs 必须有 isolated attempt output、shared atomic winner lock、loser receipt、pending loser cancellation。
- V100 兼容必须显式声明，不得为了 16 GB 显存偷偷改变科学语义。

## 6. Planner 输出必须包含

每条 route 的合同必须包含：

- route objective。
- branch 和 worktree。
- exact write scopes。
- forbidden writes。
- architecture/dataflow。
- modules to implement。
- implementation gate。
- training/evaluation gate。
- Slurm plan / partition compatibility。
- expected outputs。
- result packet contract。
- validator known-bad cases。
- reviewer checklist。
- stop/continue criteria。
- finalizer behavior。
- allowed and forbidden tokens。

每条 route 的 executor plan YAML 必须明确：

- route_id。
- execution_mode。
- controller_supervised 是否需要。
- executor_slots。
- parallel_execution_allowed。
- write scopes。
- read-only inputs。
- Slurm permissions。
- partition compatibility。
- implementation-before-training gate。
- finalizer / validator requirements。

## 7. Critic 请求

每条 route 必须生成独立 critic request。Critic 必须检查：

- 是否真实保留该 route 的架构思想。
- 是否存在 placeholder / mock / declaration-only 绕过点。
- 是否有 implementation gate。
- 是否允许未验收就训练。
- 是否混用 worktree 或 result namespace。
- 是否错误写 `prompts/shared/`。
- 是否把 pending Slurm 当完成。
- 是否有 reviewer-independent evidence。
- 是否把 Route A/B 错称为 milestone。
- 是否清楚 Cine 也必须做。

Critic 通过 token 建议：

```text
ROUTE_A_PLANNING_READY_FOR_CONTROLLER
ROUTE_B_PLANNING_READY_FOR_CONTROLLER
ROUTE_C_PLANNING_READY_FOR_CONTROLLER
```

这些 token 只授权后续 route controller 启动，不授权 validation upload、route promotion、M11、final scientific conclusion 或跨 route merge。

## 8. 最终汇报

完成后汇报：

- 每条 route 推送到哪个 branch。
- 每条 route 的 commit SHA。
- 每条 route 的 contract path。
- 每条 route 的 executor plan path。
- 每条 route 的 critic request path。
- 是否修改了 `prompts/shared/`；如修改，必须说明必要性。
- 是否所有 route 都仍从最新 `main` / setup commit 派生。

不要执行代码、不要训练、不要提交 Slurm、不要启动 controller。
