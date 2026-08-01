---
task_key: 20260801_care_ase_final_model
task_kind: scientific_milestone
task_type: final_asymmetric_pathology_model
status: DRAFT_NOT_AUTHORIZED
risk_level: critical
route_change: false
scientific_decision_scope: promotion_candidate
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
executor_slots: 3
executor_count: 3
parallel_execution_allowed: true
mapper_slots: 1
mapper_required: true
architecture_impact: system
wiki_update_required: true
diagram_update_required: true
slurm_runtime_continuity_required: true
continuity_backend: tmux_watcher
planning_review_required: true
review_required: true
allow_git_commit: false
auto_git_commit: false
allow_git_push: false
auto_git_push: false
allow_diagnostic_push: false
new_training_authorized: false
validation_upload_authorized: false
docker_upload_authorized: false
hosted_metric_claim_authorized: false
blueprint_path: prompts/blueprints/CARE_ASE_final_model_blueprint_20260801.md
implementation_contract_path: prompts/blueprints/CARE_ASE_exact_implementation_contract_20260801.yaml
---

# CARE-ASE Final Model Controller — DRAFT FOR GPT CRITIC

> 本文件只是待审 Controller 草案。当前不得执行、训练、提交作业、修改 CURRENT/wiki 或 push。只有 GPT Critic 明确给出 `CARE_ASE_CONTROLLER_APPROVED`，并由用户再次授权后，才能把 frontmatter 改为正式执行合同。

## 1. Controller 唯一任务

严格按以下两个冻结文件实现和训练 CARE-ASE：

```text
prompts/blueprints/CARE_ASE_final_model_blueprint_20260801.md
prompts/blueprints/CARE_ASE_exact_implementation_contract_20260801.yaml
```

Controller 和 Executor 不得：

- 缩小网络；
- 删除分支、head、loss或训练stage；
- 用lite/placeholder/proxy替代；
- 因实现缺口写`NEEDS_IMPLEMENTATION`后退出；
- 因早期指标差跳过正式训练；
- 恢复任何合同禁止的历史机制；
- 把“文件存在、forward成功、梯度非零”写成科学成功。

## 2. 正式执行前必须被 Critic 审核的内容

Critic 必须逐项确认：

1. 设计是否真正不同于nnU-Net统一六类头和MoSAIC独立多网络级联。
2. 完整stock encoder/decoder是否保持，且final pathology不依赖stock class4/5 logits。
3. scar proposal、scar full-res decoder、edema full-volume decoder、soft-wall、slice extent是否均有精确tensor流和final权限。
4. no-T2所有edema梯度是否严格为0。
5. M0R、M1、M2、M3、A0-A3、PRISM、MyoWall、QIF暴露的问题是否均有防复发门。
6. W1/W2发现缺口时是否强制修复，而非No-Run。
7. W3是否只依赖implementation PASS，且Stage A/B/C无科学提前停止。
8. 14000步、full-volume evaluator、物理HD/remote-FP、sentinel cases是否冻结。
9. Controller是否还存在`optional/TBD/as appropriate/Codex decide`等设计空白。
10. 资源、Slurm和resume合同是否足以让formal run真实完成。

## 3. 预期并行角色

正式授权后只允许三个 Executor：

```text
Executor-1: MODEL_AND_LOSS
  实现CareASEModel全部模块、loss、intervention和unit tests。

Executor-2: DATA_AND_SAMPLING
  实现manifest、OOF error sampler、distance/rho targets、no-T2 mask、batch descriptors。

Executor-3: TRAIN_EVAL_RUNTIME
  实现trainer、checkpoint/reload、full-volume evaluator、Slurm wrappers、resume和accounting。
```

三个Executor必须从同一main SHA建立local-only worktree；只允许local commits，不允许各自push。Controller在implementation与test通过后按固定顺序合并：

```text
DATA_AND_SAMPLING
MODEL_AND_LOSS
TRAIN_EVAL_RUNTIME
INTEGRATION
```

任何冲突由Controller按冻结合同解决，不能删模块换取合并方便。

## 4. 强制任务图

```text
W0 远端同步、协议/图/证据读取、split/checkpoint/plan冻结
 ↓
W1 三Executor并行完成全部实现
 ↓
W2 真实病例preflight + mandatory repair loop
 ↓
W3 fold2/fold3并行14000步正式训练
 ↓
W4 checkpoint reload + inner full-volume selection
 ↓
W5 outer一次性评价 + module interventions + hard-case atlas
 ↓
W6 mapper + validator + independent reviewer
 ↓
W7 用户授权后才允许commit/push/notify
```

### No-Run硬规则

- `W1`发现任何缺module/adapter/head/loss/sampler/evaluator，必须在本Goal修复；`NEEDS_IMPLEMENTATION`不是终态。
- `W2`每类失败最多3次同合同repair；只有数据/checkpoint不可读、资源永久不可用、三次修复后仍无法真实forward/backward才可block。
- `W3`只依赖`IMPLEMENTATION_PASS`，不得依赖Stage A中间Dice、loss或视觉结果。
- Stage A、B、C全部必须完成；不得early stop、缩短步数、跳过complete-case target-domain阶段。
- Formal jobs必须在W2通过后由Controller自动启动；不得停下来等待用户再发prompt。
- `submitted`、`pending`、`running`、`preempted`、`startup_failed`均不是完成。
- Controller必须持续到所有job/step terminal、sacct/accounting闭合、aggregation完成。

## 5. W0 强制读取

正式版必须先fetch/pull最新main，并完整读取：

```text
AGENTS.md
START_HERE_FOR_GPT.md
GPT_PLANNER_CARE_PROTOCOL.md
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

CARE-ASE blueprint and exact contract
results/20260801_care_nnunet_mosaic_complementarity_closure/**
results/20260801_care_four_lane_evidence_reconciliation/**
results/20260730_care_failure_forensics_deep_research_packet/**
results/20260731_care_myopath_a0_a3_full_volume_closure/**
results/20260731_care_myowall_geometry_diagnostic_closure/**
results/20260731_care_qif_v2_signal_audit/**
docs/presentation/20260801/presentation-final.pdf
```

视觉读取并记录：

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

W0必须产出：

```text
controller_context.json
source_commit_and_hash_manifest.json
stock_fold2_fold3_checkpoint_manifest.json
plans_and_architecture_receipt.json
split_receipt.json
sentinel_case_contract.json
```

## 6. W1实现必须一次闭合

所有required files/classes由exact contract确定。W1结束时必须有真实代码和测试，不接受设计说明代替实现。

Controller必须用AST/runtime检查拒绝：

- `pass`、`NotImplementedError`、固定零tensor或随机输出；
- module声明但forward未调用；
- loss声明但不进入L_total；
- stock class4/5 logits进入final；
- D0后两层浅head冒充独立decoder；
- permanent frozen trunk；
- hard-negative manifest未被sampler读取；
- no-T2仍对edema branch产生非零梯度；
- hard ROI/hard wall/scar-priority重新出现。

W1每个Executor必须做local commit并写：

```text
implementation_snapshot.md
source_diff_summary.md
contract_coverage.json
remaining_gap_count: 0
```

只要`remaining_gap_count > 0`，不能进入W2，也不能终止Goal，必须继续实现。

## 7. W2真实preflight

至少用以下真实病例：

```text
complete CenterB: Case2019
complete CenterC: Case3008
LGE-only: Case1045
LGE+C0: Case7009
```

必须完成：

1. stock compatibility mode FP32 parity；
2. CARE-ASE normal forward输出所有合同key；
3. 每项loss finite且denominator正确；
4. 每个required module直接梯度；
5. no-T2 edema全部梯度0；
6. one-batch overfit：scar、edema和final6均明显下降；
7. save/reload parity；
8. full-volume one-case sliding-window inference；
9. module on/off改变对应中间输出和final labels；
10. known-bad fixtures全部fail closed。

Preflight失败必须进入repair loop。每次repair保持blueprint、split、budget和metric不变；记录attempt、diff、failure和resolution。

## 8. W3正式训练草案

正式版建议两个fold并行：

```text
fold2: one GPU
fold3: one GPU
```

每fold固定：

```text
Stage A 2000 steps
Stage B 8000 steps
Stage C 4000 steps
total 14000
```

Checkpoint：每1000步；full-volume inner每2000步。必须保存model、optimizer、scheduler、GradScaler、RNG、sampler cursor、batch descriptor cursor，以支持exact resume。

正式作业不得使用裸`python`，必须使用：

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python
```

Draft资源建议：

```text
partition: htzhulab preferred
GPU: 1 per fold
CPU: 16
memory: 128G
walltime: 18h
```

若允许复用interactive allocation，Controller应先占用interactive GPU训练一个fold，另一个fold排队；interactive完成后自动接管仍pending的fold。该调度必须在正式Controller中写死，不能由Codex临时决定。

## 9. W4/W5评价

Checkpoint选择只使用inner。Scar和edema可选择不同step，但必须分别reload。Outer之前写`checkpoint_freeze_receipt.json`，此后禁止改step、阈值、logit系数和decode。

Outer只评价一次，并使用canonical physical metric。固定atlas至少包含：

```text
Case3008 Case3009 Case3027 Case3012 Case2034 Case2025
Case2019 Case2012 Case2009 Case1045 Case1029 Case8021
```

每例显示：

```text
LGE/T2/C0
GT
stock nnU-Net
CARE-ASE
scar proposal/center/context
edema injury/extent/boundary
soft-wall context
scar/edema FP/FN
module-off variants
```

必须由Controller视觉检查病例ID、slice、orientation、label和prediction source。

## 10. W6 Reviewer硬门

Independent reviewer必须只读检查：

- 实现是否忠实；
- 14000步是否足额；
- no-T2是否无泄漏；
- stock pathology shortcut是否不存在；
- extent/soft-wall/proposal/context是否真实进入final；
- outer是否只读一次；
- promotion token是否与机器指标一致；
- negative是否为faithful negative。

Reviewer只允许：

```text
CARE_ASE_REVIEW_PASS
CARE_ASE_REVIEW_REVISE_IMPLEMENTATION
CARE_ASE_REVIEW_REVISE_EVIDENCE
```

Reviewer未PASS不得更新CURRENT/wiki为candidate，不得进入commit/push。

## 11. 未来正式Controller必须新增的known-bad

至少覆盖exact contract中的23项，并额外覆盖：

1. Wave以`NO_RUN`结束。
2. Wave以`PREFLIGHT_NEEDS_IMPLEMENTATION`结束。
3. Stage A低分导致Stage B/C未运行。
4. Executor输出future work而非代码。
5. Controller在pending状态退出。
6. 14000步被epoch换算错误缩短。
7. fold2/fold3只跑一个。
8. full-volume inner evaluator实际使用patch proxy。
9. module intervention只看logit均值，不看final labels。
10. reviewer未PASS仍push candidate状态。

## 12. 当前草案的提交边界

当前文件是draft：

```text
allow_execution: false
allow_training: false
allow_slurm_submission: false
allow_current_or_wiki_update: false
allow_commit_push_notify: false
```

GPT Critic完成后，应输出一份明确diff建议。只有用户批准后，才创建正式controller/executor-plan并授权执行。