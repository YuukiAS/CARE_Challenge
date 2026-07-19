# Round03 Route Architecture Audit

## Scope

This report maps Route B and Route C architecture evidence at the end of Round03. It does not train, submit Slurm jobs, start controllers, package validation, upload validation, promote a route, start M11, merge across routes, claim hosted metrics, or make a final scientific decision.

Active repository: `/users/a/e/aereinh/CARE`.

Remote repository: `YuukiAS/CARE_Challenge`.

## Source Of Truth

Repository state checked after `git fetch --all --prune` on 2026-07-19:

| Worktree | Branch | HEAD | Status |
| --- | --- | --- | --- |
| `/users/a/e/aereinh/CARE` | `main` | `30098813522cecd98e60bcb99e2676b28c1a5461` | behind `origin/main` by 8; existing user dirty files present |
| `/users/a/e/aereinh/CARE_worktrees/route_B` | `route_B` | `b9c7664da7cb1f1892fff37a4497722f31a0a96d` | clean |
| `/users/a/e/aereinh/CARE_worktrees/route_C` | `route_C` | `17062b00edc3443aacefe8583568797a9f2655ba` | clean |

User dirty files in `main` were not edited: `prompts/routes/handoffs/CURRENT.md`, `prompts/routes/route_B_round04_controller_contract.md`, `prompts/routes/route_B_round04_critic_request.md`, `prompts/routes/route_B_round04_executor_plan.yaml`, `scripts/ops/build_route_watchboard.py`, and `tests/ops/test_build_route_watchboard.py`.

Required rule and skill files read included `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/HANDOFF_GATE_POLICY.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, `prompts/routes/README.md`, `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`, `prompts/routes/handoffs/CURRENT.md`, `routes/README.md`, `wiki/README.md`, `.agents/skills/care-mapper/SKILL.md`, `.agents/skills/scientific-visualization/SKILL.md`, `.agents/skills/d2-diagrams/SKILL.md`, and `.agents/skills/markdown-mermaid-writing/SKILL.md`.

The repo-local Markdown skill referenced `.agents/skills/markdown-mermaid-writing/references/markdown_style_guide.md`, but that file does not exist in this checkout. The missing reference is recorded here rather than inferred.

## Diagram Legend

| Status | Meaning |
| --- | --- |
| Green solid | implemented + reviewer verified |
| Blue dashed | implemented or smoke evidenced, not formal runtime complete |
| Yellow dashed | planned / scaffolded / unexecuted |
| Red solid | blocked / adequate negative / needs revision |
| Gray dashed | stale historical evidence |
| Purple dashed | forbidden authority boundary |

Generated D2 sources and renders:

| Diagram | D2 source | SVG | PNG |
| --- | --- | --- | --- |
| Route B structure | `docs/figures/round03_route_architecture/round03_routeB_structure.d2` | `docs/figures/round03_route_architecture/round03_routeB_structure.svg` | `docs/figures/round03_route_architecture/round03_routeB_structure.png` |
| Route C structure | `docs/figures/round03_route_architecture/round03_routeC_structure.d2` | `docs/figures/round03_route_architecture/round03_routeC_structure.svg` | `docs/figures/round03_route_architecture/round03_routeC_structure.png` |
| Route B vs Route C gap | `docs/figures/round03_route_architecture/round03_routeB_vs_routeC_gap.d2` | `docs/figures/round03_route_architecture/round03_routeB_vs_routeC_gap.svg` | `docs/figures/round03_route_architecture/round03_routeB_vs_routeC_gap.png` |

## Route B Actual Round03 Status

Route B Round03 is a reviewer-accepted B3 adequate negative / partial evidence packet, not a full-route negative. The latest Route B reviewer file at `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/review.md` emits `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`.

The supported facts are:

| Stage | Actual Round03 status |
| --- | --- |
| B0 | manifests/source probe were present and may be inherited only after a fresh fingerprint audit |
| B1 | route-local SRR scaffold existed: four-scale model, 16 experts per scale, OOF prototype contract, Cine interfaces |
| B2 | implementation/smoke gate passed: forward, gradients, save/reload, export QA, official CineMA smoke, registration/temporal smoke |
| B3 | formal warmup reached 43003 optimizer steps, 1800.7964860140346 train-loop seconds, and 22 validation events |
| B3 failure | `anatomy_union_overfit=false`; this is the actual Round03 block |
| B4-B9 | no formal Round03 packets; proposal, refiner, joint selector, official CineMA matched control, faithful registration, and registered temporal aggregation did not execute |
| B10 | terminal accounting and strict validator passed; packet was not monitor-only |

The reviewer explicitly states that B4-B9 absence is justified only because the Round03 executor plan treated B3 as a blocking terminal gate. It does not prove that those downstream modules failed.

## Route B Intended Architecture

The Round04 planning files describe the intended full SRR-v3 Route B architecture. They are architecture targets and pending work, not completed Round03 evidence.

Required SRR-v3 target modules:

| Module | Intended structure | Current evidence status |
| --- | --- | --- |
| Inputs | `[B,3,Z,H,W]`, modality order `[LGE,T2,C0]`, availability `[B,3]` | implemented/smoke evidenced |
| Stems and scales | modality stems with multi-scale channels `[32,64,128,256]` | implemented/smoke evidenced |
| Expert bank | 16 experts per scale, shared/private/interaction families | implemented/smoke evidenced |
| Family masks and router | anatomy/scar/edema masks, two-pass spatial router, invalid logits masking | B3 invalid-slot evidence reviewer verified; full final-path effect not complete |
| Pattern-SIP | entmax/top scheduling target, group mass/floor loss | contracted and smoke evidenced; formal full-path contribution pending |
| Anatomy repair | union/LV/RV targets with anchor localization floor | planned Round04 repair |
| OOF prototypes and hard negatives | shard discipline, frozen OOF banks, no-T2 exclusion | planned Round04 B4 |
| Proposal/refiner | separate scar/edema proposals, soft ROI, separate refiners | code/scaffold smoke only; formal B4/B5 pending |
| Bounded final composition | bounded residual correction, no-T2 exact-zero, official six-label export | B2/B3 smoke and safety evidence; formal B6 pending |
| CineMA chain | official CineMA, matched random control, registration, registered temporal fusion | CineMA smoke exists; formal B7-B9 pending |

Round04 source files read include `prompts/routes/route_B_round04_controller_contract.md`, `prompts/routes/route_B_round04_executor_plan.yaml`, `prompts/routes/route_B_round04_critic_request.md`, `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`, and `prompts/routes/route_B_round04_critic_review.md`.

`prompts/routes/route_B_round04_coordinator_receipt.md` is referenced by `CURRENT.md` and the critic request but is missing in this local `main` checkout.

## Route B Gaps

The core gap is not that Route B lacks any code shape. The gap is that Round03 stopped at a B3 representation/anatomy gate before lesion formation and Cine fidelity were exercised.

Key gaps:

| Gap | Why it matters |
| --- | --- |
| B3 auxiliary gate was route-global in Round03 | `anatomy_union_overfit=false` blocked progression before proposal/refiner/Cine could be tested |
| No B4-B6 MyoPS terminal evidence | no OOF proposal training, no refiner training, no joint selector, no 44-case same-split help/harm, no full final-output ablation |
| No B7-B9 Cine terminal evidence | no formal official CineMA matched random control, no case-level learned/SyN registration evidence, no registered temporal final-output rows |
| Round04 planning is not controller-ready | current critic token is `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION`, not `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` |
| Main worktree state is not clean/current | `main` is behind origin and has user dirty changes; this audit avoids overwriting those files |

Therefore Route B should be handed to Round04 as a revised full SRR-v3 plan requiring critic-ready binding and B0-B10 controller execution, not as a completed Round03 candidate or final scientific stop.

## Route C Actual Round03 Status

Route C latest independent reviewer decision is `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`, from `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/review.md`.

Route C controller completed the assigned Round03 repair after an inherited R1 blocker. The controller report records fresh repair job `59530203` as `COMPLETED` with exit `0:0`. The final packet is not monitor-only. R3 runtime job `59501370` and finalizer job `59501378` are terminal, with finalizer state `PASS`.

The latest reviewer also confirms that Route C remains blocked from validation upload, route promotion, M11, cross-route merge, hosted metric claims, and final scientific decision. The evidence-complete token is only for portfolio reconciliation.

## Route C Implemented Architecture And Evidence Chain

Route C implements a fuller evidence chain across R1, R2, and R3.

| Area | Implemented evidence | Reviewer status |
| --- | --- | --- |
| R1 known-bad repair | 88 positive/negative prototype swap rows; all detected harmful; 17633 changed voxels total; 80/88 rows with changed components | reviewer verified |
| R1 zero-effect controls | 88 no-op rows and 88 anchor residual off rows remain zero-effect | reviewer verified |
| R1 validators | strict R1 and final validators passed; old bad packet covered by tests | reviewer verified |
| R2 CineMA | official CineMA provenance, commit/revision/weight SHA/license, logits/probs/features/entropy, matched random control | reviewer verified |
| R3 registration | seven-step SVF, true Jacobian, real SyN rows, 60 pair receipts, 12/12 case gate pass | reviewer verified |
| R3 temporal | consumes registered logits/features/uncertainty, velocity, displacement, Jacobian, motion, texture residual, frame quality, temporal position, valid masks | reviewer verified |
| R3 final output | 12 temporal final-output rows show changed logits/voxels/components | reviewer verified |

Implementation files read for Route C include:

| Path | Role |
| --- | --- |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/route_C/myops/evidence_contract.py` | fail-closed MyoPS evidence contract |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/route_C/cine/fidelity.py` | Cine fidelity preflight, 7-step integration, true Jacobian, temporal adapter |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/cinema_adapter.py` | CineMA adapter and compact Cine labels |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/registration_model.py` | learned registration U-Net and warp helpers |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_dictionary.py` | eight-slot temporal dictionary |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_model.py` | registration-gated temporal segmentation model |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_output.py` | local temporal output and real SyN helper path |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/models/proposal_prototypes.py` | prototype bank and no-T2-safe negatives |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/models/srr_propref.py` | proposal/refinement SRR model |

## Route C Stale Or Conflicting Evidence

`/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/architecture_delta_final.md` says the final evidence state is not ready and requires revision/evidence. That conflicts with the newer independent review in `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/review.md`.

This report treats `architecture_delta_final.md` as stale historical evidence. It is retained as provenance of an older mapper state and must not override `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`.

## Route B vs Route C Comparison

| Dimension | Route B Round03 | Route C Round03 |
| --- | --- | --- |
| Final reviewer token | `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE` | `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE` |
| Scope of token | B3 terminal gate only; downstream stages not tested | repaired R1 plus retained R2/R3 evidence chain |
| MyoPS final-output evidence | B2 smoke and B3 safety/accounting; no B6 terminal evidence | D2/D3 interventions and repaired known-bad swap verified |
| CineMA | official-source smoke in B2; matched random formal lane pending | official source, weight SHA/license, logits/features/entropy, matched random control verified |
| Registration | smoke/scaffold only for Round03 | 7-step SVF, true Jacobian, real SyN, 60 pair receipts, 12/12 case gate pass |
| Temporal | interface smoke only for Round03 | registered temporal consumption and 12 changed final-output rows verified |
| Main limitation | B4-B9 unexecuted; Round04 planning still critic-needs-revision | evidence-complete does not equal route promotion or final scientific conclusion |

## Round04 Handoff

Recommended handoff:

| Recipient | Handoff item |
| --- | --- |
| Main/planner | Treat Route B Round03 as B3 adequate negative only; preserve full SRR-v3 Round04 target and repair critic blockers before controller start |
| Route B critic | Re-review the final bound Round04 planning files after `CURRENT.md`, B10 reachability, per-executor validators, and executable receipt are repaired |
| Route B controller | Start only after exact `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER`; execute B0-B10 without converting planned modules into evidence |
| Route B reviewer | Check B4-B9 terminal evidence and B10 accounting; reject monitor-only, smoke-only, or B3-only evidence as full-route completion |
| Route C planner/reconciler | Use latest reviewer token as evidence-complete input for portfolio reconciliation |
| Route C reviewer | If re-opened, use latest `review.md` over stale `architecture_delta_final.md` |
| All roles | Keep validation upload, route promotion, hosted metric claim, M11, cross-route merge, and final scientific decision blocked until separately authorized |

## Path Existence Notes

All paths listed as source or evidence in `round03_route_architecture_components.csv` were checked. Missing paths are represented by empty evidence fields or explicit notes. The notable missing path is `prompts/routes/route_B_round04_coordinator_receipt.md`.
