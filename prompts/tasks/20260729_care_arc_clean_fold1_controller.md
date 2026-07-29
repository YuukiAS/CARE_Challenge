# CARE-ARC clean fold1 Controller Prompt

你是 CARE Challenge 项目的 Controller / Coordinator。当前任务不是继续 DPR Gate B-R2，也不是在 nnU-Net 上增加一个新 residual head，而是执行新的 CARE-ARC 单主干、双病理直接完整重建主线。

仓库：

```text
/users/a/e/aereinh/CARE
```

远端与分支：

```text
YuukiAS/CARE_Challenge
main
```

## 0. 开始前同步与 authority

先执行 `git fetch origin`，同步最新 `origin/main`。确认最新 main 至少包含：

```text
f3cc5afa3cff7f2fbf8be8b6ec7945170839eac2
  Record DPR Gate B R2 stopped partial status

e89d39528f9af0a0cb36a2694f651748847e4b41
  Add CARE-ARC anchor-relaxed reconstruction blueprint

845c2dfcf508d7a06ba85487cdd96d933e47f115
  Add CARE-ARC clean fold1 executor plan
```

必须读取：

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
prompts/blueprints/CARE_ARC_anchor_relaxed_complete_reconstruction_20260729.md
prompts/tasks/20260729_care_arc_clean_fold1_executor_plan.yaml
```

`CURRENT.md` 和 root wiki仍可能停留在 2026-07-26 baseline-only状态。必须标记为 stale evidence，使用最新 main、DPR-R2 stop packet和本任务合同作为当前执行真值；在 Mapper final 前不得把目标架构写成已验证。

任务优先级：

```text
CARE-ARC blueprint
> CARE-ARC executor plan
> 本 Controller prompt
> stale CURRENT/wiki
> 历史 DG/DPR/Cascade/MMRD task
```

## 1. 当前事实和科学动机

必须在 Controller bootstrap 中明确记录：

- CARE-DG/SCR拼接 validation probe scar 为 `0.6211 / 15.1513`，略高于nnU-Net但低于MoSAIC `0.6965 / 13.7827`；
- hidden逐病例观察显示CARE probe的scar/edema几乎始终贴近nnU-Net，而MoSAIC更倾向完整、高召回、连续病灶；
- DPR Gate B-R1完成候选级训练修复后，complete16三项Dice仍全部略低于nnU-Net；
- DPR Gate B-R2 partial inner search完成925/1200 rows，eligible=0，最佳平均Dice delta约 `-0.0319`，继续接受更多local candidates会同时破坏Dice、HD95、remote FP和help/harm；
- 因此本任务停止“围绕anchor做局部修补”，改为scar/edema direct complete reconstruction。

不得把这些事实解释为放弃CARE。它们是 CARE-ARC 的设计动机。

## 2. 唯一架构

CARE-ARC必须严格实现：

```text
[LGE,T2,C0] + availability
-> modality-specific residual stems
-> one identity-initialized bounded LGE-reference alignment block
-> one CARE-owned ResEncM-style shared encoder
   -> internal anatomy decoder
   -> scar evidence gate -> scar coarse extent -> scar direct reconstruction
      -> scar presence + contour mean/logvar
   -> edema evidence gate -> edema coarse extent -> edema-zone direct reconstruction
      -> edema presence + contour mean/logvar
-> direct edema-zone mask
-> direct scar mask
-> scar priority
-> pure edema = edema-zone minus scar
```

强制规则：

1. 主体只有一个 shared backbone。
2. nnU-Net可以提供：
   - same-fold encoder shape-compatible初始化；
   - anatomy probabilities 0–3；
   - uncertainty和distance context；
   -非病理final labels；
   -灾难性asset/grid fallback。
3. nnU-Net scar/edema probabilities不得成为CARE direct pathology decoders的必要输入，也不得定义final病理mask邻域。
4. MoSAIC不得进入runtime、teacher、ensemble或初始化。
5. 不允许MMRD teacher、多backbone、第二个U-Net、prototype、dictionary、router、component utility或ADD/REVISE arbitration。
6. Scar和edema必须结构对称、参数独立、采样平衡、分别报告。
7. Edema只在T2-present可靠病例监督；no-T2 edema output/loss/gradient为零。

## 3. Agent graph和执行顺序

严格按 executor plan 顺序运行：

```text
W0 adoption and truth freeze
-> W1 implementation
-> W2 real-case preflight
-> W3 fold0 zero-credit development diagnostic
-> W4 fold1 clean formal training and one-time outer evaluation
-> W5 clean gate / mapper final / packet
-> W6 only if W5 clean gate passes: single-backbone full-data fit and local package dry-run
```

只允许：

```yaml
executor_slots: 1
executor_count: 1
mapper_slots: 1
parallel_execution_allowed: false
```

Controller必须检查Executor真实diff、入口、loss wiring、数据采样、train/inference parity和required outputs。普通实现问题必须退回同一Executor原地修复，不得直接写科学失败。

## 4. 唯一GPU资源

当前唯一允许资源：

```text
jobid: 61220581
partition: htzhulab
node: g1807htzh01
gpu: H100 NVL
```

每次GPU wave前必须现场检查：

```bash
squeue -j 61220581
scontrol show job 61220581
srun --jobid=61220581 --overlap --ntasks=1 bash -lc 'nvidia-smi'
pgrep -af 'care_arc|care_dpr|python.*CARE' || true
```

所有GPU命令只能串行：

```bash
srun --jobid=61220581 --overlap --ntasks=1 bash -lc '<command>'
```

严格禁止：

```text
sbatch
salloc
新Slurm job
并行两个GPU进程
写 /overflow/htzhu/CARE
```

若 `61220581` 终止，只能返回：

```text
OPERATIONALLY_BLOCKED_ALLOCATION_61220581_TERMINATED
```

并记录精确resume point。不得提交新job。

## 5. W0：收养新合同并冻结真值

生成：

```text
results/20260729_care_arc_clean_fold1/controller_context.json
results/20260729_care_arc_clean_fold1/controller_bootstrap_snapshot.md
results/20260729_care_arc_clean_fold1/controller_ledger.csv
results/20260729_care_arc_clean_fold1/adoption_receipt.json
```

必须记录：

- git HEAD / origin/main；
- blueprint、executor plan、AGENTS、Slurm skill和Mapper skill hashes；
- allocation 61220581 live state；
- 当前GPU进程；
-工作树已有diff/untracked分类；
- `f3cc5afa...` DPR-R2 partial stop证据；
- DPR-R2 `925/1200`, `eligible=0`, best avg delta `-0.031935...`；
- `CURRENT.md` / wiki stale状态；
-当前任务禁止validation/Docker upload。

不得删除旧DPR runtime或证据。

## 6. W1：实现门

必须真实实现这些文件或等价、但路径不得缺失：

```text
src/care_myocardium/models/care_arc.py
src/care_myocardium/data/care_arc_dataset.py
src/care_myocardium/training/care_arc_trainer.py
src/care_myocardium/inference/care_arc_predictor.py
scripts/training/run_care_arc.py
scripts/evaluation/evaluate_care_arc.py
scripts/evaluation/validate_care_arc_packet.py
tests/care_arc/
configs/care_arc/
```

### 6.1 主干和初始化

- 一个CARE-owned ResEncM-style encoder；
- 三个modality-specific residual stems；
- same-fold Dataset501 nnU-Net encoder只允许shape-compatible初始化deeper encoder blocks；
- clean fold1不得载入任何包含fold1 outer cases的DPR/MMRD/ARC checkpoint；
- 初始化receipt必须列出每个loaded/skipped/random parameter和来源hash。

### 6.2 Alignment

-仅在1/4分辨率一次；
- LGE reference；
- C0/T2 bounded offsets每轴 `[-4,4]`；
- confidence blend；
- identity initialization；
- 无第二registration encoder。

### 6.3 Direct branches

Scar和edema-zone都必须有：

```text
coarse extent
full-resolution direct logit
presence logit
signed-distance mean
signed-distance log variance
```

Scar使用LGE高分辨率skip；edema使用T2主导和更大感受野。两条branch参数独立。

### 6.4 禁止anchor dependency

Known-bad必须真实拒绝：

- CARE direct scar/edema logits必须读取nnU-Net pathology probability才能运行；
- final pathology只允许在nnU-Net当前positive区域出现；
-病理输出是anchor + bounded delta；
- component utility或ADD/REVISE仍在formal runtime；
- 一个shared pathology head冒充双分支；
- no-T2病例产生edema direct logits或gradient；
- alignment是第二backbone；
-模型只在scar上有gradient，edema为空。

## 7. W2：真实病例preflight

只用allocation 61220581。

必须覆盖：

- LGE-only；
- C0+LGE；
- C0+LGE+T2；
- scar-positive；
- edema-positive；
- hard-negative；
- no-T2。

300-step whole-heart crop overfit：

```text
crop: 8x192x192
batch: 2
formal scientific credit: 0
```

最低门：

- scar active loss下降 `>=30%`；
- edema active loss下降 `>=30%`；
- coarse/direct/presence/SDF/alignment均有真实非零梯度；
- direct masks与nnU-Net pathology mask非identity；
- alignment identity initialization和offset bound PASS；
- no-T2 edema output/loss/gradient exact zero；
- checkpoint save/reload/resume exact；
- tests、known-bad、strict preflight validator PASS。

不通过时只能同范围修复W1/W2，不能跳入正式训练。

## 8. W3：fold0开发诊断

W3是zero-credit development diagnostic，不是clean gate。

固定：

```text
fold: 0
seed: 20260729
A0: 500 steps
A1: 1500 steps
B: 1000 steps
总计: 3000 optimizer steps
batch: 2
crop: 8x192x192
checkpoint: every 500
```

可以读取fold0 complete16做development diagnosis，因为fold0已经被历史DG/DPR反复使用；但不得将结果写成clean promotion evidence。

只允许根据fold0发现**执行错误**返回W1修复。若只是科学指标不佳，仍按冻结CARE-ARC合同进入fold1 clean，不得在fold0继续threshold或结构搜索。

必须输出：

```text
EXECUTION_FAILURE
ENCODER_LIMITED
ALIGNMENT_LIMITED
DETECTION_LIMITED
CONTOUR_LIMITED
DOMAIN_CALIBRATION_LIMITED
```

中的一项或多项诊断。

## 9. W4：fold1 clean formal

固定：

```text
fold: 1
seed: 20260729
A0: 500
A1: 3500
B: 3000
总计: 7000 optimizer steps
batch: 2
crop: 8x192x192
checkpoint: every 500
```

Stage A case group抽样：

```text
complete-trimodal: 0.50
C0+LGE: 0.25
LGE-only: 0.25
```

Stage B：

```text
complete-trimodal only
center-balanced
all-model lr 2e-5
```

其余：

```text
AdamW
encoder lr A: 2e-5
CARE modules lr A: 1e-4
weight decay: 1e-4
bfloat16
grad clip: 1.0
```

严格要求：

- fold1初始化只来自fold1-safe Dataset501 encoder；
-不得加载fold0 DPR/MMRD/ARC；
- checkpoint、scar/edema threshold、minimum component volume、presence empty rescue只能用fold1 train-side inner选择；
- scar和edema分别选择；
- outer fold1只评价一次；
- outer结果产生后不得重选参数；
-不得使用MoSAIC predictions、weights或runtime。

## 10. W5：clean科学门

同一canonical evaluator分别报告：

```text
scar
edema-zone
pure-edema
```

指标：

```text
Dice
HD95
exact HD
precision
recall
volume ratio
component count
remote FP
positive-GT empty rate
case-wise help/harm
```

机制：

```text
coarse extent AUPRC/component recall
presence AUROC/AUPRC
SDF contour error/uncertainty calibration
alignment offset/confidence
identity-vs-aligned control
evidence-gate weights
direct-mask changed-voxel ratio
T2-present/no-T2
CenterB/CenterC
```

Clean gate必须全部满足：

1. 三病理Dice delta均 `>=-0.005`；
2. scar或edema-zone至少一个 `>=+0.010`；
3. 另一个主病理 `>=0.000`；
4. 每病理help `>= harm-1`；
5. HD95 `<=1.05x anchor`；
6. 无新增infinite exact-HD；
7. remote FP `<=1.10x anchor`；
8. positive empty不高于anchor；
9. scar和edema在至少50%的positive cases中changed pathology voxels ratio `>=5%`；
10. 两病理coarse/direct/presence/contour真实激活；
11. no-T2 edema exact-zero；
12. no-alignment control完整报告。

Validator必须从casewise和summary独立重算，不得只读取预写status。

若不通过：

- 不得写项目停止或恢复nnU-Net-only为研究终态；
-不得自动调整fold1并再次评价；
-完整分类执行/编码/对齐/检测/轮廓/域校准缺口；
-完成terminal packet、发送邮件并返回Planner；
-保持allocation holder，不主动新建job。

## 11. W6：仅clean gate通过时

clean fold1通过后，自动继续一个single-backbone full-data fit：

```text
seed: 20260729
A0: 500
A1: 4500
B: 4000
总计: 9000 optimizer steps
batch: 2
crop: 8x192x192
```

使用fold1 inner已冻结的：

- scar threshold；
- edema threshold；
- minimum component volume；
- presence empty-rescue；
- alignment/postprocess/TTA contract。

只准备本地validation package dry-run和deterministic hashes。禁止上传。

## 12. Mapper、wiki和finalizer

本任务改变architecture、loss和dataflow，必须运行Mapper draft/final。

实现完成前，wiki只能写planned/unverified；clean fold完成后按真实证据更新：

```text
wiki/README.md
wiki/MODEL.md
wiki/EXECUTION.md
wiki/COMPONENTS.csv
wiki/LINEAGE.md
wiki/architecture.yaml
wiki/current_state.yaml
wiki/figures/*.d2
wiki/figures/*.svg
wiki/figures/*.png
prompts/routes/handoffs/CURRENT.md
```

必须运行：

```bash
./envs/env_CARE/bin/python scripts/architecture/validate_care_architecture_wiki.py --strict
./envs/env_CARE/bin/python scripts/architecture/generate_care_architecture_wiki.py --check
```

Controller必须负责到所有GPU步骤terminal、aggregation、strict validators、Mapper final和lightweight local commit完成。

默认runtime roles不得push。用户已授权本次GPT规划文件push，不等于授权Controller runtime push。

## 13. 完成邮件

只有terminal aggregation、validator、Mapper final和lightweight commit完成后，复用现有 notifier向：

```text
1155246312@link.cuhk.edu.hk
```

发送中文短邮件。

Clean gate通过并完成full-data local candidate：

```text
Subject: [CARE-ARC] clean fold通过并完成full-data本地候选，等待上传决策
```

Clean gate未通过但诊断完成：

```text
Subject: [CARE-ARC] clean fold结果完成，已定位下一轮完整修复方向
```

邮件必须说明：

- clean fold结论；
- scar/edema/pure-edema Dice与HD95相对nnU-Net；
- direct-mask非identity；
- no-T2；
- alignment/no-alignment；
- full-data是否运行；
- validation/Docker未上传；
-下一步需要Planner决定。

不得在running、monitor或未完成aggregation时发送。

## 14. 最终状态字段

Controller report必须包含：

```text
controller_verification_decision: VERIFIED_COMPLETE | NEEDS_REPAIR | OPERATIONALLY_BLOCKED
operational_completion_status:
experiment_adequacy_decision:
contract_compliance_status:
clean_fold_scientific_gate:
scar_result:
edema_zone_result:
pure_edema_result:
direct_reconstruction_nonidentity:
no_t2_safety:
fold_expansion_decision:
full_data_fit_status:
validation_upload_authorized: false
docker_upload_authorized: false
git_commit_decision:
git_push_decision: NOT_AUTHORIZED
next_required_action: RETURN_TO_PLANNER | CONTINUE_CURRENT_TASK | HUMAN_INTERVENTION_REQUIRED
```

`VERIFIED_COMPLETE`只代表当前合同执行完成，不自动授权validation upload或Docker upload。
