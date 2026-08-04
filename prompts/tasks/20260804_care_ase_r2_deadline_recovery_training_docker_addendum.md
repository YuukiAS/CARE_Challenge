# CARE-ASE 截止日前恢复训练补充合同

本文件是
`prompts/tasks/20260804_care_ase_r2_deadline_recovery_training_docker.md`
的同任务补充合同。它不创建新 Goal，不替换原任务，不重新设计模型，也不授权 outer、validation 上传、Docker 上传或发送邮件。

当前绝对时间边界以香港时间为准：

```text
官方字面截止：2026-08-04 15:59 HKT
内部完成线：2026-08-04 14:59 HKT
```

Controller 必须在 14:59 前完成：可用 checkpoint 冻结、真实 inner 比较、CARE-ASE 或 fallback 决策，以及 Docker checkpoint 注入所需的全部准备。14:59–15:59 只允许最终 build/load/run/save/hash 或直接使用已验证 fallback，不再训练、不再改科学实现。

## 一、不要重置已经恢复的 Controller

若原 Goal 已运行：

- 继续同一个 Controller/tmux；
- 读取本文件后更新当前 ledger；
- 不得再创建第三个大型 Goal；
- 不得因为读取本文件而自动终止已正常运行的训练；
- 只有下列 P0 在训练尚未产生有效 checkpoint，或确认会使结果/比较错误时，才允许停止两折、修复并从 step0 重启。

若训练尚未启动，下面 P0 必须先完成，但总计不得超过 25 分钟。

## 二、当前已确认的成绩与公平比较 P0

### P0-1：评估必须使用 checkpoint 的真实 global step

当前 inner monitor 调用 canonical full-volume inference 时，不能依赖 `global_step=14000` 默认值。

必须从 checkpoint payload 读取：

```text
checkpoint_step = payload["global_optimizer_step"]
```

并显式传入：

```python
predict_care_ase_r2_full_volume_logits(
    ...,
    global_step=checkpoint_step,
)
```

原因：extent ramp 在 step<=500 为0、500–2000渐增。用 14000 评估 step250/500/1000 checkpoint 会提前施加完整 extent bias，可能制造虚假的 edema/scar 退化或提升。

修复范围必须覆盖：

```text
scripts/evaluation/care_ase/monitor_care_ase_r2_inner_trend.py
任何 deadline fast-panel wrapper
CARE-ASE checkpoint候选比较
未完成14000步时的Docker推理配置
```

完整 step14000 checkpoint 仍使用 14000。

### P0-2：CARE-ASE 与 nnU-Net 必须使用同一 TTA/滑窗语义

当前 canonical settings 默认 `use_mirroring=false`，而冻结 stock OOF producer 使用 nnU-Net predictor 的 mirroring/TTA。这样不是公平比较，也可能低估 CARE-ASE。

必须从当前 Dataset501 stock plans/augmentation contract 和 stock predictor 读取并冻结：

```text
tile_step_size
gaussian_sigma_scale
use_gaussian
use_mirroring
allowed_mirror_axes
padding/slicer
precision
decode
```

不得凭记忆硬编码 mirror axes。CARE-ASE panel、最终 checkpoint selection、host inference 和 Docker 必须使用同一 settings receipt。

新增或运行数值检查：

```text
step0 CARE-ASE vs 对应fold stock nnU-Net
同病例、同输入、同TTA、同滑窗、extent ramp=0
argmax changed voxels = 0
anatomy/scar/edema logits max error在冻结容差内
```

step0 parity 不通过是实现/推理错误，必须在正式训练前修复；不能把它当早期低分。

### P0-3：nnU-Net baseline物理指标必须从真实 OOF 数组重新计算

旧 `oof_complementarity_casewise.csv` 可以提供 frozen case mapping 和 Dice参考，但其中很多 `nnunet_hd95_mm` 为 `BOUND_METRIC_NOT_AVAILABLE`。不得在缺失时用 CARE-ASE 自己的 HD95 代替 baseline，从而把 HD95 delta伪装为0。

每个 frozen panel case必须读取其真正 patient-held-out stock OOF prediction，在同一 preprocessed grid 上用同一 metric实现计算：

```text
Dice
HD95 mm
exact HD mm
precision
sensitivity
volume ratio
component count
remote FP count/volume >10mm
blood-pool-adjacent FP
lesion recall
small-lesion recall <1000mm3
```

优先复用已存在的 direct preprocessed-grid OOF arrays/manifest。缺失时只允许对 frozen panel case fresh运行对应 held-out stock fold，不重跑全220例。

Baseline packet必须绑定：

```text
case_id
source stock fold
checkpoint path/SHA
prediction array SHA
GT SHA
spacing
metric implementation SHA
```

### P0-4：small-lesion recall必须是component级指标

不得把“小scar病例上的体素 sensitivity”命名为 `small_lesion_recall`。

固定定义：

1. 在GT scar中按26-connectivity分component；
2. 使用真实spacing计算每个component体积；
3. 只保留 `<1000 mm3` component；
4. 每个component与预测scar有至少一个体素重叠时记为recalled；
5. `small_lesion_recall = recalled_small_components / total_small_components`。

同一实现同时用于 CARE-ASE 和 stock baseline。

### P0-5：deadline monitor必须接受任意 verified checkpoint step

当前 monitor 的固定 choices `4000,6000,...` 与当前剩余时间不相容。监控脚本必须区分：

```text
trend mode：接受任意 1..14000 的 verified checkpoint
formal selector mode：只接受合同允许的候选集合
```

本次 deadline recovery 使用 trend mode，不得因为 checkpoint 是250/500/750/1000而拒绝。

Checkpoint step必须同时核对：

```text
CLI step
payload global_optimizer_step
verified receipt global_step
checkpoint filename
```

## 三、训练源码的最后检查

以下当前实现已做过修复，Controller只做针对性确认，不再开放式审计：

```text
OOF类别无坐标时不得伪装为OOF
small scar按mm3而非voxel数
remote background使用>10mm物理距离
blood-pool adjacent使用<=3mm且不在血池内
edema boundary使用physical EDT
requested/resolved category与selected coordinate一致
no-T2不进入edema图或class4竞争
full-case target manifest在forward前核验
```

若当前 main 回退任一项，必须立即修复。否则不得继续增加测试或重写系统。

允许的最后速度优化只有：

```text
case image/seg/properties只读cache
target cache扩大或node-local复用
non-log step collect_metrics=false
日志批量flush
移除不必要的逐micro CPU同步
pinned-memory/non-blocking H2D
```

禁止改变：

```text
模型结构
loss及权重
patch size
四microbatch
augmentation
Stage定义
采样比例
precision语义
label/decode
```

## 四、正式训练与fair comparison节奏

两折仍固定并行：

```text
61794608 -> fold1
61830309 -> fold4
```

若 allocation失效，按原恢复 Goal 的 replacement/race规则处理。

### 4.1 Checkpoint节奏

从 step0 开始，每250个完整 optimizer steps保存并reload验证：

```text
250, 500, 750, 1000, 1250, ...
```

收到signal时在最后完整step另存 verified checkpoint。

### 4.2 固定公平面板

训练启动前冻结，不得按结果换病例：

```text
MINI_PANEL：每fold 2例
- 1例scar hard case
- 1例T2-present edema hard case

FAST_PANEL：每fold 6例
- CenterB tri-modal
- CenterC tri-modal
- small scar
- scar remote-FP risk
- edema under-activation
- edema over-extent
```

不得包含outer。

固定运行计划：

```text
step0：MINI_PANEL，证明与stock parity
每个250-step checkpoint：MINI_PANEL真实full-volume比较
step500、step1000及最终checkpoint：FAST_PANEL真实full-volume比较
若实际速度未达到这些step：每60分钟对最新verified checkpoint跑一次MINI_PANEL
14:15前最后checkpoint：必须跑FAST_PANEL
```

训练与panel不能同时抢同一GPU导致OOM。允许在checkpoint后短暂停训执行panel，完成后从verified checkpoint恢复；也允许有安全第三GPU时异步执行。所有panel必须记录实际耗时。

每轮用户可读摘要必须至少包含：

```text
fold / checkpoint step / Stage
scar Dice及delta vs held-out stock
pure-edema Dice及delta vs held-out stock
HD95
precision / sensitivity
volume ratio
empty prediction
component count
remote FP
small-lesion recall
case-wise help/harm
CenterB / CenterC
```

不得只报告loss。

## 五、2–3小时早期根因门

在训练启动后约2小时和3小时各做一次合并诊断。低分只在存在下列可证明异常时触发源码修复：

```text
step0 parity失败
checkpoint/恢复不一致
NaN/Inf
no-T2 edema泄漏
scar或edema大面积全空/全满
volume ratio系统性<0.1或>10
CARE与stock比较使用了不同TTA/spacing/decode
extent ramp使用错误step
sampler requested/resolved/coordinate名实不符
关键branch/loss梯度恒零
训练日志显示Stage/LR/trainability错误
```

根因报告必须区分：

```text
implementation bug
numeric/runtime bug
data/metric mismatch
ordinary undertraining
```

只有前三类允许改源码。普通 undertraining 不允许改架构、loss权重、阈值、采样比例或跳Stage。

最后允许的source-changing修复截止：

```text
2026-08-04 11:45 HKT
```

发生修复时：

1. 两折停止在完整step；
2. 提交一个小型明确修复commit；
3. 重建source manifest/runtime bundle/permit；
4. 两折从step0重启；
5. 不再等待Planner/GPT复核；
6. 11:45后禁止再改训练科学源码，只做运行恢复、比较和Docker准备。

## 六、绝对收尾时间

```text
14:10：停止产生新的科学源码修改
14:15：两折保存最后完整step verified checkpoint
14:15–14:45：并行完成最终FAST_PANEL、checkpoint reload和候选判断
14:45：冻结 CARE-ASE candidate或fallback
14:45–14:59：把选中checkpoint、settings、label mapping和运行命令放入Docker staging；确认一键build入口
14:59：训练、选择、模型决策和Docker准备必须结束
15:59：官方提交硬截止
```

CARE-ASE进入Docker至少要求：

```text
reload PASS
step0 parity与no-T2 safety PASS
无catastrophic collapse
FAST_PANEL多数病例不显著受损
至少scar或edema出现可信正向信号
无明显volume/remote-FP爆炸
```

不满足时立即冻结已验证 fallback，不得在最后一小时继续追分。

## 七、Docker只做增量准备

不得破坏、覆盖或重新上传现有已验证 fallback archives。

训练运行期间只完成 CARE-ASE 增量层：

```text
checkpoint注入位置
self-contained inference loader
canonical full-volume settings receipt
compact->official label mapping
geometry restoration
/input/myops -> /output/myops接口
host/container equivalence命令
Dockerfile checkpoint-last-layer设计
一键build/save/hash脚本
```

13:30前这些内容必须完成，不等最终checkpoint。

14:45后只需要：

```text
复制冻结checkpoint
build/load
至少1例黑盒运行
host/container voxel+geometry等价
save gzip-1
SHA256
```

若时间不足，14:59时必须保证现有 fallback archive、SHA、公开链接和邮件草稿仍可直接使用。

## 八、Controller最终边界

Controller不得在以下状态退出：

```text
RUNNING
PENDING
NEEDS_MONITOR
无fair comparison
只有loss
只有step数
没有Docker staging
```

14:59前必须在thread和结果目录给出多轮表格，并明确：

```text
实际训练step/Stage
每轮fair comparison
是否发现并修复实现问题
最终CARE-ASE或fallback决策
Docker staging完成度
剩余最后一小时精确命令
outer/upload/email均未执行
```

本补充合同不得被解释为重新开启无限返修。