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
- Route C 未读取或未继承旧 M10/follow-up/follow-up2 硬要求。

## Planner 输出底线

每个 portfolio round planner 必须为 Route A、Route B、Route C 都产出 controller-forward work，并准备 route-specific critic handoff 或 critic-ready request。Critic 通过前，controller 不应启动。

失败可以接受，低目标假推进不接受。一个能跑通但没有 leaderboard-facing rationale、没有三主指标目标、没有同一划分 baseline、没有困难子组 help/harm、没有 reviewer 可审计 evidence 的计划，不是合格的 CARE route plan。
