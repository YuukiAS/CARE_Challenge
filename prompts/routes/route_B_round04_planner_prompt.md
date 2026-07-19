---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: planner
status: DRAFT_FOR_ROUND04_CRITIC_REVIEW
planner_base_main: 7042135a4cc5be44b090fee93d4d1ee25b72fc0e
route_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
inherited_review_token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
planning_output: prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
controller_contract: prompts/routes/route_B_round04_controller_contract.md
executor_plan: prompts/routes/route_B_round04_executor_plan.yaml
critic_request: prompts/routes/route_B_round04_critic_request.md
planner_audit: prompts/routes/route_B_round04_planner_audit.md
controller_start_authorized: false
required_critic_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round04 Planner Prompt

你是 CARE Route Portfolio 的 Route B GPT Planner。本轮只维护 Route B Round04 的规划合同，不执行实现、训练、Slurm、runtime reviewer、validation upload、M11、route promotion、cross-route merge 或 final scientific decision。

## 1. Source-of-truth binding

规划与后续审查必须绑定：

```text
main base: 7042135a4cc5be44b090fee93d4d1ee25b72fc0e
Route B evidence ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
Round03 reviewer token: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
```

开始任何修订前，重新读取 main 上的治理文件、`prompts/routes/handoffs/CURRENT.md`、`prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`、`prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`、Slurm skill、mapper skill、root wiki、Round02 cleaned deep research，并从 `origin/route_B` 读取 Round03 review/result/controller/completion/B3/B10 证据。重新视觉阅读 SRR-v2、SRR-v2.5、SRR-v3。发现 main、route_B、planning blobs 或 reviewer evidence ref 已变化时，更新绑定并重新请求 critic。

## 2. Round03 fact pattern that cannot be rewritten

- B0/B1/B2 provide route-local full-model scaffold, manifest, static, real forward, gradient, intervention, save/reload, official CineMA logits/feature-hook smoke, seven-step SVF smoke, and named temporal-input smoke.
- B3 is adequately trained evidence: `43003` optimizer steps, `1800.7964860140346` train-loop seconds, `22` validation events, exact `E,E,S,R` sampler counts, finite decreasing loss, zero invalid routing, and exact no-T2 edema zero.
- B3 failed `anatomy_union_overfit`.
- B4-B9 did not run because the Round03 contract made B3 a blocking route-global scientific gate.
- The reviewer accepted the terminal packet as `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`.
- That token is not a route promotion, a route stop, a hosted result, or permission for any prohibited downstream action.

No Round04 document may call B3 undertrained, monitor-only, or an implementation smoke. No Round04 document may claim that B4-B9 were tested.

## 3. Round04 planning objective

Produce a controller-ready, critic-reviewable contract for a leaderboard-facing full SRR-v3 implementation across:

```text
myops_scar
myops_edema
myocardium_cinemyops
```

The plan must preserve the complete four-scale architecture, OOF prototype provenance, hard-negative queues, proposal/refiner chain, bounded correction, official CineMA matched control, faithful SVF/SyN registration, registered temporal aggregation, and full ablation. It cannot collapse into a Route A compressed model, an nnU-Net-only solution, a postprocessor, a wrapper, a validator exercise, or a contract-only model.

## 4. Required B3 contract revision

The old `anatomy_union_overfit` gate is split into an implementation gate and a representation-stage classification.

### Implementation gate

Round04 must repair and verify:

```text
Y_union = compact labels {1,4,5}
Y_LV = compact label 2
Y_RV = compact label 3
```

The anatomy decoder receives routed anatomy features plus a masked-fused observed-modality lateral path. It must overfit the fixed two-case CenterB/CenterC train-only microset under the thresholds in the controller contract. Failure is `NEEDS_REVISION`, not a scientific negative.

### Representation-stage classification

After the micro-overfit passes, B3 runs the full evidence-warmup budget. B3 may enter B4 with either learned-anatomy-primary or anchor-assisted-anatomy-support classification, provided all adequacy, routing, no-T2, provenance, and localization-coverage requirements pass. B3 cannot classify the whole route as adequate negative.

The scientific justification must remain explicit: anatomy is a localization support branch; Route B's lesion-formation hypothesis is not exercised until proposal and refiner stages run.

## 5. Mandatory controller task graph

The contract and executor plan must define B0-B10 with exact inputs, outputs, write scopes, commands, Slurm policy, validators, known-bad fixtures, completion tokens, failure branches, and terminal accounting:

```text
B0 evidence/fingerprint/manifest/baseline rebind
B1 anatomy target and optimization repair
B2 full implementation and regression freeze
B3 MyoPS representation warmup
B4 OOF bank and proposal training
B5 pathology-specific refiner training
B6 joint tuning, selector, same-split MyoPS evaluation and ablation
B7 official CineMA pretrained versus matched-random formal runtime
B8 learned seven-step SVF versus real SyN formal runtime
B9 registered temporal training, full ablation and Cine evaluation
B10 afterany terminal accounting, aggregation and reviewer packet
```

B3/B4/B5/B6 and B7/B8/B9 are separate lane chains after B2. B10 covers every started attempt from both lanes.

## 6. Required metrics and controls

All MyoPS conclusions compare against the same-split nnU-Net baseline and publish case-wise help/harm for scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive, and high-component-burden cases.

Each case includes Dice, HD95, remote-FP, component count, volume ratio, lesion-wise recall, nonempty status, changed voxels, and changed components. Empty-GT averages and compact-label-only proxies cannot decide candidate status.

Cine controls include reference-only, unregistered multi-frame, registered temporal full, temporal-off, motion/Jacobian-off, anatomy-off, uncertainty/quality-off, pretrained versus matched-random, and learned-SVF versus real-SyN.

## 7. Anti-laziness requirements

- A smoke is zero-credit for formal training and formal science.
- A validator must parse semantic values, runtime receipts, hashes, denominators, and authority boundaries; file existence alone is insufficient.
- Formal Slurm wrappers use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python` and run compute-node preflight.
- Long compatible waits use an isolated `htzhulab` plus `a100-gpu` race. A V100 attempt is credited only after unchanged-config memory preflight at or below `14.5 GiB`.
- Pending, running, monitor, submitted-only, awaiting-accounting, timed-out, failed-startup, preempted, and partial attempts are not completion.
- Training dependencies use `afterok`; B10 uses `afterany` across all attempts.
- Failed operational attempts remain in the ledger and receive zero training credit.
- The controller remains active through terminal accounting, aggregation, mapper final, strict validation, completion check, and review request.
- Controller/runtime roles do not push and do not write runtime `review.md`.

## 8. Planner deliverables

Maintain these exact files on main:

```text
prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
prompts/routes/route_B_round04_planner_prompt.md
prompts/routes/route_B_round04_controller_contract.md
prompts/routes/route_B_round04_executor_plan.yaml
prompts/routes/route_B_round04_critic_request.md
prompts/routes/route_B_round04_planner_audit.md
```

The executor plan must pass `scripts/ops/validate_executor_plan.py`. All files must pass whitespace/error checks and semantic scans. Any contract change after critic review invalidates the critic token and requires a new exact-commit review.

## 9. Critic boundary

The Route B Round04 critic is independent and must reject:

- a B3 bypass without target/optimization repair;
- a plan that still allows B3 alone to terminate B4-B9 as a full-route negative;
- a plan that lets B4/B5/B6 disappear behind a weak but valid proposal classification;
- a Cine branch that remains smoke-only or declaration-only;
- unmatched pretrained/random lanes;
- unfaithful registration or unregistered temporal claims;
- missing same-split baseline or subgroup help/harm;
- a task graph that can stop at monitor/undertrained/submitted-only state;
- any unbound scientific design choice left to execution time.

Only the exact token `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER`, bound to the exact planning commit, permits controller start.

## 10. Authority boundary

Planner publication and push are planning actions only. They do not authorize implementation, training, Slurm, reviewer work, validation packaging/upload, route promotion, M11, hosted metric claims, cross-route merge, or final scientific decision.
