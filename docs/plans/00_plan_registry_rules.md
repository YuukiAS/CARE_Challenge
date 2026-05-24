# CARE Myocardium Plan Registry And Rules

Date: 2026-05-20

本目录是 CARE Myocardium 的计划控制台。`/overflow/htzhu/CARE/TODO.md` 是长期路线图；本目录里的 plan 是可执行控制文档。后续每一轮只新增或更新对应 lane/round 的 plan，不把 controller、round addendum、repo portfolio governance、执行日志混在同一个文件里。

Plan metadata:
- Type: plan registry and naming rules
- Lane: all CARE Myocardium lanes
- Round scope: all rounds
- Status: active rule source for `docs/plans`
- Parent roadmap: `/overflow/htzhu/CARE/TODO.md`
- Parent plan: none
- Function: define file naming, plan roles, round ownership, and conflict handling for future plan generation
- Do not: use ambiguous plan filenames or silently override this registry when a prompt conflicts with it

## 当前项目阶段

`TODO.md` 将当前阶段定义为：

> CARE-native targeted mechanism testing, between Round2 and Round3.

也就是说，项目已经完成 baseline exit-gate 和 failure landscape mapping；现在进入 CARE-native mechanism testing。当前不应继续围绕 `third_party/MyoPS-Net`、`third_party/U-MyoPS`、`third_party/CineMyoPS` 做无边界 patch，也不应直接启动大规模 repo portfolio integration。Round3 的重点是：

- Lane A：MyoPS edema 进入 trainable smoke，先做 loss/gradient/tiny-overfit，再考虑 fold0 short train。
- Lane B：Cine topology LCC 进入 hosted calibration preparation，先做 packaging/raw-label QA，是否上传是后续单独决策。
- Lane C：portfolio/DA 只做 governance 和低成本 audit；外部 repo 大规模接入推迟到 Round5。

## Round Definitions

| round | name | status | purpose | plan relationship |
| --- | --- | --- | --- | --- |
| Round0 | baseline interpretation and paper-baseline exit-gate | completed | 判断 MyoPS-Net/U-MyoPS/CineMyoPS 是否继续作为主线；保留负证据和 nnU-Net operational baseline。 | Reflected in lane controller plans and README/TODO. |
| Round1 | protocol anchor and failure landscape mapping | completed | 固定 nnU-Net501/502 anchors、fold、label mapping、unified evaluator、modality/center stratification、failure registry。 | Reflected in controllers; do not create new Round1 plans unless reconstructing evidence. |
| Round2 | targeted diagnostic smoke | completed / evidence stage | Lane A 验证 edema postprocess 是负信号；Lane B 验证 topology LCC 是正信号。 | `laneA_round02_completed_myops_edema_targeted_smoke_addendum.md`, `laneB_round02_completed_cinemyops_topology_lcc_addendum.md`. |
| Round3 | targeted trainable smoke and hosted calibration | next | Lane A 做 training-side edema mechanism smoke；Lane B 做 topology_lcc validation-style QA/hosted calibration preparation；Lane C 只做必要 audit。 | Create new `laneA_round03_next_<topic>_execution.md` and/or `laneB_round03_next_<topic>_execution.md`. |
| Round4 | CARE-first skeleton extraction | pending Round3 signal | 把通过 smoke 的模块抽到 `src/`，形成 CARE-native substrate。 | Add `round04_pending_src_skeleton_extraction_plan.md` only after Round3 positive signal. |
| Round5 | repo portfolio integration | pending Round3/Round4 | 按机制槽位接入外部 repo/weights，不做无差别 repo race。 | Governed by `laneC_round03to05_governance_portfolio_repo_screening_da_plan.md`. |
| Round6 | fold expansion and submission strategy | pending fold0 success | 对通过 fold0 gate 的方法扩 folds，准备 one-zip validation submission。 | Add submission/fold expansion plan only after local gates pass. |

## Current Plan Inventory

| file | type | lane | round scope | status | function | next action |
| --- | --- | --- | --- | --- | --- | --- |
| `laneA_round03plus_controller_myops_modality_aware_src_plan.md` | controller | Lane A, MyoPS scar/edema | Round3+ | active controller | 定义 MyoPS first-party `src/` 主线、Dataset501/fold/label/eval 约束、候选机制和 promotion gates。 | Keep stable; add Round3 execution addendum instead of editing controller for every experiment. |
| `laneA_round02_completed_myops_edema_targeted_smoke_addendum.md` | round addendum | Lane A | Round2 | completed/evidence addendum | 记录 edema-focused diagnostic smoke 的机制映射、候选、输出和 stop criteria；Round2 结果已说明 postprocess-only edema cleanup 不是主线。 | Use as input for Round3 trainable smoke; do not extend with new unrelated future mechanisms. |
| `laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md` | controller | Lane B, CineMyoPS / `myocardium_cinemyops` | Round3+ | active controller | 定义 Cine hosted/HD repair、topology gates、one-zip submission semantics、future motion/strain/pretrained-cine route。 | Keep stable; create Round3 hosted calibration addendum next. |
| `laneB_round02_completed_cinemyops_topology_lcc_addendum.md` | round addendum | Lane B | Round2 | completed/evidence addendum | 记录 topology/LCC smoke 的设计、positive signal、raw-label topology QC 和 future extraction targets。 | Use as input for Round3 hosted calibration; do not expand into large temporal backbone planning here. |
| `laneC_round03to05_governance_portfolio_repo_screening_da_plan.md` | governance/controller | Lane C, portfolio / DA / normalization | Round3-Round5 | active governance | 统一外部 repo、pretrained weights、loss/postprocess、DA/normalization 的筛查、合规和 fail-fast 规则。 | Use when deciding whether a repo/weight/loss may enter Round5 or a small Round3/4 smoke. |

## Round3 Plan Slots To Add Next

| proposed file | lane | purpose | allowed actions | explicitly disallowed |
| --- | --- | --- | --- | --- |
| `laneB_round03_next_hosted_calibration_execution.md` | Lane B | Prepare topology_lcc validation-style QA and candidate package manifest using nnU-Net MyoPS + Cine topology_lcc branch. | raw-label QA, component/bbox/volume tables, manifest proof, optional package preparation if explicitly requested. | automatic upload, new training, external weights, cine-only submission framing. |
| `laneA_round03_next_edema_trainable_smoke_execution.md` | Lane A | Convert Round2 negative edema postprocess result into trainable smoke: edema loss gradients, tiny overfit, then optional fold0 short train. | loss/unit tests, tiny-overfit diagnostics, <=8h fold0 train only after smoke passes. | fold expansion, new backbone, external repo integration, pseudo-labeling. |
| `laneC_round03_next_normalization_audit_execution.md` | Lane C | Optional low-cost center/modality intensity/error audit only if needed to choose Lane A normalization/routing. | robust-z/clipping/statistics audit, CARE-only tables. | heavy adversarial DA, diffusion harmonization, external data, validation pathology pseudo-label training. |

## Naming Rules For Future Plans

Plan filenames under `docs/plans/` must include lane, round scope, role/status, and topic. Do **not** create vague names such as `next_plan.md`, `implementation_plan.md`, `laneA_plan.md`, or `round3.md`.

Use these exact patterns:

| plan kind | filename pattern | example |
| --- | --- | --- |
| registry/rules | `00_plan_registry_rules.md` | `00_plan_registry_rules.md` |
| lane controller | `lane<LETTER>_round<NN>plus_controller_<topic>_plan.md` | `laneA_round03plus_controller_myops_modality_aware_src_plan.md` |
| completed round evidence/addendum | `lane<LETTER>_round<NN>_completed_<topic>_addendum.md` | `laneB_round02_completed_cinemyops_topology_lcc_addendum.md` |
| next/planned round execution | `lane<LETTER>_round<NN>_next_<topic>_execution.md` | `laneA_round03_next_edema_trainable_smoke_execution.md` |
| active/in-progress round execution | `lane<LETTER>_round<NN>_active_<topic>_execution.md` | `laneB_round03_active_hosted_calibration_execution.md` |
| cross-lane execution | `round<NN>_<status>_cross_lane_<topic>_plan.md` | `round03_next_cross_lane_execution_plan.md` |
| portfolio/governance | `laneC_round<NN>to<MM>_governance_<topic>_plan.md` | `laneC_round03to05_governance_portfolio_repo_screening_da_plan.md` |

Round numbers are always zero-padded two digits: `round02`, `round03`, `round04`. Use `round03plus` for durable controllers that begin at Round3 and remain active later. Use `round03to05` for governance documents spanning a bounded range.

Each plan must start with this metadata block:

```text
Plan metadata:
- Type:
- Lane:
- Round scope:
- Status:
- Parent roadmap:
- Parent plan:
- Function:
- Do not:
```

## Conflict Rule

If a future user prompt, ChatGPT-generated instruction, or agent-generated filename conflicts with this registry or with `TODO.md`, the agent must **not** silently comply. It must stop before writing the conflicting plan, state the exact conflict, and ask the user to decide.

Examples that require escalation to the user:

- Prompt asks for `docs/plans/implementation_plan.md`, but the plan is really Lane A Round3. The compliant name should be `laneA_round03_next_<topic>_execution.md`.
- Prompt asks to update a controller for one round of execution; the compliant action is to create a round addendum instead.
- Prompt asks to start Round5 repo portfolio integration while `TODO.md` says Round3/Round4 gates have not passed.
- Prompt asks for a Cine-only validation plan that ignores one-zip MyoPS+Cine submission semantics.

If the user explicitly chooses to override the rule, record the exception in the plan metadata under `Rule exception:` with the user's reason.

## Editing Rules

- `TODO.md` remains the long-term roadmap; do not duplicate the whole roadmap in every plan.
- Controller plans define durable lane rules. Do not rewrite them for every experiment; add a round addendum.
- Round addenda are scoped to one lane and one round. Mark them completed/evidence once the round result is known.
- Lane C does not mean “run DA as a standalone mainline”; it governs portfolio/weights/loss/DA eligibility.
- Do not start Round5 repo portfolio integration until Round3/Round4 identify which mechanism slot needs an external repo.
- Do not plan validation uploads as lane-specific uploads. One validation zip contains both `MyoPS/` and `CineMyoPS/` and returns three metrics.
