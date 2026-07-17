# CARE Route Hard Requirements Matrix

本文是 Route A、Route B、Route C 后续所有 portfolio round 的永久强要求矩阵。它不是 Round02 专用文件。任何 GPT 规划者、规划审查者、Codex 控制者、验证者、终结者和审阅者，在处理 CARE 三路线时都必须读取并执行本文。

本文与 `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md` 配套使用：

- `ROUTE_ANTI_LAZINESS_PROTOCOL.md` 记录偷懒模式和执行期底线。
- 本文记录三条 route 各自持续继承哪些科学目标、旧 milestone 硬门槛和规划审查要求。

## 永久规则

后续 `round03`、`round04` 及任何新 round 都必须继续适用本文。不得因为 round 编号变化、旧 milestone 迁移到 route portfolio、或某一轮 handoff 没有逐字复制本文，就弱化这些要求。

每个新的 portfolio planner handoff 必须明确引用本文，并说明本轮是否仍按本文继承。默认答案必须是“仍继承”。任何删除、降级或暂缓本文要求的行为，都需要用户明确授权，并在 handoff 中写出被修改的具体条目、原因和影响。

## 三路线共同要求

所有 route 都必须是 leaderboard-facing，不只是 runnable。每条 route 的计划和审查都必须围绕 CARE Myocardium 三个主指标：

- `myops_scar`
- `myops_edema`
- `myocardium_cinemyops`

不允许用 `foreground_mean`、empty-GT improvement、compact-label proxy、local proxy-only metric、工程可运行状态、validator pass 或 smoke pass 掩盖三项主指标失败。

每条 route 的 planner 输出必须包含：

- 本轮目标指标和 expected gain mechanism。
- 与同一划分 nnU-Net baseline 的比较。
- case-wise help/harm matrix。
- 失败判据和停止/继续条件。
- T2-present edema、no-T2 safety、CenterB/CenterC、scar-positive、remote FP、component count、`Dice`、`HD95`、volume ratio 等困难子组和安全矩阵。
- `diagram_versions_read`、`visual_read_status`，以及从 SRR 图恢复的 route objective。
- exact controller task graph、write scopes、required files、validators、known-bad fixtures、finalizer behavior、reviewer pass requirement。
- minimum effective training 或 evidence classification 字段。
- 如果涉及 Slurm，必须有 Python/env/`torch`/CUDA preflight，禁止正式 Slurm wrapper 使用裸 `python`。
- training-to-training dependency 使用 `afterok`；finalizer/accounting dependency 使用 `afterany`。
- terminal accounting 和 post-completion aggregation 后才能请求 review。
- strict validator 必须 fail closed；known-bad fixtures 必须覆盖语义绕过，而不是只检查文件存在。
- 架构、loss、dataflow、export、Cine temporal 或 mapper/fingerprint 变化必须有 route-local mapper/fingerprint receipt。
- 只发布 lightweight evidence：小型 Markdown/CSV/JSON 和必要的一方 source/helper/test；禁止提交 checkpoint、NIfTI、raw data、大日志、secret、upload package 或 hosted submission artifact。

## 禁止空白授权

Planner 和 critic 必须把计划写到 controller 可以直接照做的程度。不得把科学设计、模型结构、训练预算、数据输入、输出路径、Slurm 策略、validator 语义、known-bad、终止条件或 reviewer 通过标准留给 Codex/controller 自行决定。

以下写法在 route plan、critic handoff、executor plan 或 controller prompt 中默认不合格，除非同一句或同一小节给出明确条件、默认值、允许范围、证据要求和失败处理：

- `TBD`
- `optional` / `可选`
- `as appropriate` / `where appropriate`
- `if needed` / `when needed` / `必要时` / `按需` / `视情况`
- `choose best` / `select suitable` / `合理选择`
- `Codex decide` / `controller decide` / `由 Codex 决定` / `由 controller 自行决定`
- `implement robustly` / `补一个稳健实现`
- 只写“修好 validator”“完善 known-bad”“跑足训练”“检查 Slurm”“准备 reviewer”但没有精确文件、命令、阈值、token、证据和失败分支。

允许 controller 做的决定只限于机械执行层面的同义实现选择，例如在不改变合同语义、文件路径、训练预算、指标、门槛和写作用域的前提下选择等价的代码组织方式。任何会影响科学假设、模型结构、训练/评估规模、数据划分、指标解释、Slurm partition/race、completion token、reviewer pass/fail 的选择，都必须由 planner 写清，并由 critic 审查通过。

Critic 必须把“计划留白”当作 hard-gate failure。不能因为计划看起来方向正确，就让 controller 在执行时补设计。

## M9/M10 历史硬门继续有效

以下要求来自 M9、M10、M10 follow-up 和 follow-up2 的规划审查。它们不是旧 milestone 的一次性文字，迁移到三路线后仍然是 route planning 和 critic review 的硬门。

### 机制闭环和证据命名

- evidence 文件名必须和内容一致。不能把普通 component summary、proxy matrix、usage table 或 checkpoint row 命名成 `ablation`、`causal_effect`、`intervention` 或 `fidelity`。
- 如果声称 causal effect，必须有同一 checkpoint、同一 eval cases、同一 decode rule 下的真实 on/off 或 graph-node intervention，并报告 final-label delta、Dice、HD95、remote-FP、component count、changed voxels 和 volume ratio。
- proposal、refiner、dictionary、memory、loss 和 final output 必须形成可追踪链路。典型链路是 `memory source -> proposal similarity -> proposal logits -> refiner logits -> final labels`。只写 summary JSON、slot counts 或 usage rows 不算机制闭环。
- Pattern-SIP / router / dictionary 不能只是 post-hoc summary。若把它作为卖点，必须证明它是训练目标或前向路径的一部分，并有 tensor、gradient、load/alias、invalid-slot mask 和 final-output contribution 证据。
- missing-modality private/interaction slot 必须有逐 batch、逐 task、逐 slot 的 invalid gate 检查，至少报告 max/mean invalid weight；不能只用汇总假设说 invalid slot inactive。
- scar 和 edema 不能被一个 composite mean 掩盖。scar 重点看 focal/small ROI、precision、HD95、remote-FP；edema 重点看 T2-present recall/HD95、CenterB/CenterC、no-T2 safety。
- no-T2 safety 只能证明安全，不能替代 T2-present edema 性能。synthetic T2 dropout 或 no-T2 case 不能被当成 edema negative 来提高分数。
- nnU-Net 只能作为 baseline、anchor、context、teacher、evidence 或 safety source；如果 route 声称 SRR 主体有效，必须有 SRR-owned logits/final output 或明确的 bounded residual effect，不能让 nnU-Net 成为隐式主角。
- 如果使用 SRR-main / no-context / hard-negative refresh / alignment control 等 control，必须说明它们是 scientific control、candidate 还是 negative evidence。inference-only substitute 不能冒充 retrained control。

### 合同绑定和机器可解析性

- Planner 和 critic 必须确认自己审查的是最新 planner HEAD，不得沿用 stale planning token、旧 hash 或旧 commit。必要时必须记录 merge-base、planner HEAD、critic base 和 reviewed commit。
- route contract、executor plan、critic handoff、reviewer prompt 必须机器可解析。frontmatter/body mirror、schema 字段、inline list、路径、token 和 hash 不能只在人类可读段落里出现。
- 如果使用 staged prompt 或 canonical prompt section，必须计算并记录 stable hash 或 canonical section hash。历史 hash 只能作为 provenance，不能在合同修改后复用。
- executor plan 必须通过对应 validator；human-readable plan 不能替代 `executor_plan.yaml` 或 route-specific task graph。
- diagnostic publication scope、blocked actions、git commit/push decision、review boundary 必须是机器可读字段。多行 YAML 列表若会被 parser 读成空值，必须改成 parser-compatible 表达。

### 训练、继承和 runtime 解释

- 旧 runtime 或旧 Wave 证据只能作为背景或有条件继承。必须先做 code/config/split/case/label/preprocess/decode/checkpoint/runtime fingerprint audit；不匹配的 phase 阻塞或要求明确重跑，不能静默继承。
- 失败、timeout、preempted、partial checkpoint、submitted-only 和 historical partial attempt 都是 zero-credit，除非合同明确把它们定义成诊断背景。它们不能支持 readiness、route promotion 或 scientific stop。
- matched control 必须同架构、同 cases、同 frames、同 augmentation、同 optimizer、同 budget、同 validation cadence、同 selection rule。否则不能解释 pretrained benefit、random-init noninferiority 或 architecture adequacy。
- selected checkpoint 必须 reload 后再评估或下游使用。checkpoint 名称、历史 best/final metrics 或 summary row 不能给 checkpoint formal privilege。
- negative result 只有在实现 faithful、训练充分、selected/reloaded、terminal accounting、strict aggregation 和 independent review 后，才能作为 no-promotion 或 adequate negative evidence。pipeline bug、proxy metric 或 undertraining 不能包装成科学负结果。

### Cine fidelity 和 registration 边界

- CineMA / anatomy source 必须有真实权重、license、SHA256、环境和 multiclass logits/features/uncertainty provenance。frame0 mask、binary prior、fake URL/hash 或 dataclass declaration 不能满足 readiness。
- registration 不能把 bounded velocity tensor 直接当 displacement；必须按合同保留 symmetric velocity、scaling-and-squaring、true Jacobian、inverse consistency、full loss、real ANTs/SyN control、case aggregation 和 full denominators。
- pair-level non-worse 不能冒充 case-level gate。registration gate 必须说明 denominator 是 frame pair、case 还是 sequence，并按合同聚合。
- temporal path 必须消费 selected CineMA features、registered anatomy、velocity/Jacobian/motion/uncertainty。没有 passed registration 的 temporal output、frame0 fallback、少帧 fallback 或 temporal-without-registration 都必须 fail closed。
- 如果 temporal runtime 分块执行，必须有 launch-time throughput guard、cumulative resume、atomic saves、SIGUSR1/TERM handling、parent hashes、无 reset/overlap/gap/duplicate events 证明。

### Controller/finalizer/reviewer 边界

- Long Slurm/controller-supervised work 必须有 durable finalizer contract：backend、dependency semantics、job-ID capture、runtime/log/result paths、aggregation commands、validation commands、failure states、本地轻量 commit 边界。
- training-to-training dependencies 用 `afterok`；accounting/finalizer 用 `afterany`。bounded retries 必须保持 code/config/split hash 不变并保留所有 attempt IDs。
- Mapper final 在 reviewer 前运行；wiki/current_state 不能在未 review 的 candidate 上前移。candidate snapshot 可以写成 `candidate_unreviewed`，但不能生成 route promotion 或 review token。
- Controller 和 runtime roles 不得 push、不得写 runtime `review.md`、不得 claim audited-go、route promotion、route-negative scientific closure、hosted metrics 或 final scientific decision。
- Reviewer 是独立只读后置角色。Adequate negative 也只是 no-promotion 或 scientifically unresolved evidence，不能自动变成 scientific stop。

所有 route 在用户明确授权前都禁止：

- validation packaging / upload
- route promotion
- M11
- cross-route merge
- hosted metric claim
- final scientific decision

## Route A 继承要求

Route A 永久继承强要求 1-24、34。Route A 是最快形成非纯 nnU-Net candidate 的压缩路线，但必须仍是 leaderboard-facing compressed SRR candidate，不能只是能跑通。

Route A 必须保留：

- live modality evidence，不是只读 nnU-Net output。
- availability-aware retrieval。
- anatomy-guided scar/edema proposal。
- pathology-specific refinement。
- bounded nnU-Net-anchored correction。
- no-T2 safety。
- same-split help/harm。
- real multi-frame Cine evidence，或诚实 negative/incomplete packet。
- strict validator、known-bad semantic bypass、controller/finalizer receipts 和 independent reviewer pass。
- 如果使用 dictionary、prototype memory、Pattern-SIP、proposal/refiner causal effect 或 Cine temporal，必须遵守上面的机制闭环和证据命名要求；压缩实现不允许把 proxy summary 命名成 causal/intervention/fidelity evidence。

Route A 不继承 Route C 的旧 M10 大型历史细节作为硬要求，包括：

- old M10 all-checkpoint replay。
- anchor-relative selector 完整公式。
- D2/D3 follow-up2 intervention burden。
- learned-registration fidelity contract。
- M10 large-budget training floors。
- temporal cumulative long-run schedule。

Route A critic 必须拒绝：

- nnU-Net-only
- postprocess-only
- wrapper-only
- proxy-only
- validator-only
- Cine blocker 被写成 candidate-ready
- 只修工程表面但没有 reviewer acceptance 或下一步 metric-facing 计划

## Route B 继承要求

Route B 永久继承强要求 1-24、30-34。Route B 是完整 SRR-v3 架构实现与训练路线，不能降级成 Route A 压缩版。

Route B 必须保留完整 MyoPS SRR-v3 causal chain：

- modality-specific stems
- availability-aware router
- shared/private/interaction dictionary，或明确的 optional-interaction 处理
- train/OOF prototype provenance
- anatomy decoder
- scar proposal
- edema proposal
- soft ROI
- scar refiner
- edema refiner
- bounded residual correction
- final-output intervention
- save/reload/export
- strict validation
- known-bad semantic regressions

Route B 还必须保留 M9/M10 对完整 SRR-v3 的结构精度要求：lesion/spatial-conditioned retrieval，而不是只有 global gate usage；可审查的 shared/private/interaction slot 设计；invalid-slot mask 逐 batch/task/slot evidence；Pattern-SIP 或等价 group-conditioned objective 的训练路径；train/OOF memory inventory、safe hard-negative policy、memory-to-final-label chain；scar/edema 分开的 proposal/refiner 指标和 no-context / hard-negative / alignment controls。Planner 若选择等价替代，必须逐项说明替代关系和 evidence；critic 未通过前 controller 不得自行简化。

Route B Cine 必须保留：

- real anatomy-source provenance。
- multiclass logits/features/uncertainty。
- ED/reference 和 key-frame handling。
- real registration 或 declared fixed/classical control。
- temporal aggregation 消费 registered evidence。
- final-output intervention。
- 如果使用 pretrained CineMA，必须有 matched random-init 或等价 control 才能声称 pretraining benefit。
- 如果使用 learned registration，必须保留 scaling-and-squaring、Jacobian、inverse consistency、real SyN/control、selected-checkpoint reload checks。
- 如果进入 long temporal training，必须定义 cumulative resume、zero-credit partial/timeout handling 和 parent-hash receipts。

Route B 不继承 Route C 的旧 M10 replay / 大预算作为 Round 硬要求，包括：

- old M10 all-checkpoint replay。
- anchor-relative selector 完整公式。
- D2/D3 follow-up2 evidence repair。
- M10 aggregate large-budget floors。

Route B critic 必须拒绝：

- 将完整 SRR-v3 降级为 minimal residual head。
- 把 Cine 当 optional future work。
- 把 honest blocker 当 implementation pass。
- 在 validator 未证明必要、训练语义未改变时重复已经通过的长 train/eval。
- 只修 validator/known-bad/stale token，却不说明 reviewer acceptance 和下一步 metric-facing 计划。

## Route C 继承要求

Route C 永久继承全部 34 项强要求，以及全部旧 M10 / follow-up / follow-up2 硬门槛。Route C 不做裁剪。除非用户明确授权，任何 GPT 或 Codex 都不得删除、降级或暂缓这些要求。

Route C 必须保留：

- fresh all-checkpoint replay，必须使用 `--evaluate --force`。
- per-checkpoint raw-output manifest。
- checkpoint state-dict/hash receipt。
- anchor-relative checkpoint selection，包含 `Dice`、`HD95`、remote FP、eligibility gates、calibration freeze 和 tie-breaker。
- selected-checkpoint repeat。
- D2/D3 real final-output interventions。
- deterministic clean baselines。
- no-op controls。
- known-bad positive/negative swaps。
- proposal/refiner/final-logit/final-label delta。
- changed voxels/components。
- challenge-facing metrics。
- CineMA provenance、weights、license、SHA256、multiclass logits/features/uncertainty。
- pretrained vs matched random-init control。
- selected checkpoint reload。
- faithful registration，包含 symmetric velocity、7-step scaling-and-squaring、true Jacobian、inverse consistency、full loss、real ANTs/SyN、case aggregation 和 full denominators。
- registration-negative adequacy boundaries。
- temporal evidence 消费 selected CineMA features、registered anatomy、velocity/Jacobian/motion/uncertainty。
- temporal cumulative resume、throughput guard、atomic saves、zero-credit failed/timeout/partial attempts、parent hashes。
- durable finalizer、terminal accounting、post-completion aggregation、strict validator、known-bad fixtures。
- independent read-only reviewer boundary。
- M10 complete mechanism repair 的精确结构要求：D0/D1/D2/D3 design ladder、44-case scheduled evaluation、pair-valid alignment control、no-context retrain、hard-negative refresh、exact slot-bank/router/Pattern-SIP/memory/proposal/refiner/loss/control definitions，除非用户明确授权重写。
- M10 follow-up 的机器绑定要求：latest planner ancestry、reviewed commit、stable hash/canonical hash、frontmatter/body mirror、parser-compatible publication gates、schema-valid executor plan 和 no stale planning token。
- M10 follow-up2 的 R1/R2/R3 边界：R1 只做 fresh MyoPS evidence/intervention，R2 只做 Cine implementation/tests/freeze candidate，R3 只做 frozen runtime/evidence；R3 不得编辑 code/config/scripts/jobs/wiki，implementation defect 必须 return-to-R2。

Route C critic 必须拒绝：

- 只读 Round summary，不读旧 M10/follow-up2 source。
- 降级 fresh replay、checkpoint selector、D2/D3 intervention、CineMA、registration 或 temporal fidelity。
- 把旧 partial runtime、submitted-only、pending、monitor packet 当完成。
- 把 Route C 改写成普通 Route A/B repair。
- 用 proxy metric、declaration、dataclass、mock、fake provenance 或旧 wrapper 代替真实实现。

## Critic 通用拒绝清单

任何 route critic 在当前 round handoff 指向自己的 critic prompt 后，必须拒绝以下计划：

- status-only、read-only-only、wait-only。
- runnable-only、engineering-only、proxy-only、validator-only。
- 无 leaderboard upside。
- 没有 target metrics、expected gain mechanism、same-split baseline、help/harm matrix 或 failure threshold。
- 用 `foreground_mean`、empty-GT、compact-label proxy 或 local proxy-only metric 替代主指标。
- nnU-Net-only、postprocess-only、wrapper-only、placeholder、mock、dataclass、config-only、contract-JSON-only。
- missing same-split baseline、hard subgroup matrix、no-T2 safety、real Cine evidence 或 honest blocker classification。
- pending、monitor、submitted-only、undertrained、stale token 让 controller 提前结束。
- validator 只查文件存在，known-bad 不覆盖语义绕过。
- 没有 route-specific controller-forward task graph 和 reviewer pass requirement。
- 留下设计空白，要求 Codex/controller 自行决定模型结构、训练预算、输入输出路径、Slurm 策略、validator 语义、known-bad、终止条件或 reviewer pass/fail。
- Route C 未读取或未继承旧 M10/follow-up/follow-up2 硬要求。

## Planner 输出底线

每个 portfolio round planner 必须为 Route A、Route B、Route C 都产出 controller-forward work，并准备 route-specific critic handoff 或 critic-ready request。Critic 通过前，controller 不应启动。

失败可以接受，低目标假推进不接受。一个能跑通但没有 leaderboard-facing rationale、没有三主指标目标、没有同一划分 baseline、没有困难子组 help/harm、没有 reviewer 可审计 evidence，或把关键设计留给 controller 补完的计划，不是合格的 CARE route plan。
