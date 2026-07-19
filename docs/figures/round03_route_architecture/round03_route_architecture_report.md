# Round03 Route B / Route C Model Architecture Audit

## Scope / Non-Authority Boundary

This audit repairs the Round03 route figures so they describe concrete AI model structure, tensor flow, evidence hooks, missing modules, and final-output effect. It is a mapper-style architecture audit only.

It does not train, submit Slurm jobs, start controllers or reviewers, package validation, upload validation, promote a route, start M11, merge routes, claim hosted metrics, or make a final scientific decision.

Active repository: `/users/a/e/aereinh/CARE`.

Remote: `YuukiAS/CARE_Challenge`.

Current main state after `git fetch --all --prune`:

| Worktree | Branch | HEAD | Status |
| --- | --- | --- | --- |
| `/users/a/e/aereinh/CARE` | `main` | `6c8d6f26ed4907ee59023795265ee4e1c53fb2b8` | clean and equal to `origin/main` at audit start |
| `/users/a/e/aereinh/CARE_worktrees/route_B` | `route_B` | `b9c7664da7cb1f1892fff37a4497722f31a0a96d` | clean |
| `/users/a/e/aereinh/CARE_worktrees/route_C` | `route_C` | `17062b00edc3443aacefe8583568797a9f2655ba` | clean |

Required rule and skill files were read: `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`, `wiki/README.md`, `.agents/skills/care-mapper/SKILL.md`, `.agents/skills/d2-diagrams/SKILL.md`, and `.agents/skills/scientific-visualization/SKILL.md`.

## Source Files and Evidence Inspected

Route B source-of-truth:

| Path | Role |
| --- | --- |
| `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/review.md` | latest Route B Round03 reviewer decision |
| `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/controller_report.md` | B3 terminal accounting and controller status |
| `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/round03/` | B0-B3 and B10 lightweight evidence |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/model.py` | MyoPS forward path |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/contract.py` | constants and target contract |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/cinema.py` | CineMA adapter and matched random class |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/registration.py` | SVF registration scaffold |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/temporal.py` | temporal evidence consumer |
| `/users/a/e/aereinh/CARE_worktrees/route_B/scripts/route_B_round03/` | implementation and packet scripts |
| `/users/a/e/aereinh/CARE_worktrees/route_B/scripts/training/route_B_round03/train_myops.py` | B3-B6 training stages and gates |

Route C source-of-truth:

| Path | Role |
| --- | --- |
| `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/review.md` | latest Route C Round03 reviewer decision |
| `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/controller_report.md` | repair controller status and accounting |
| `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/round03/` | R1/R2/R3 lightweight evidence |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/route_C/myops/evidence_contract.py` | R1 fail-closed evidence contract |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/route_C/cine/fidelity.py` | Cine fidelity, SVF math, and temporal adapter |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/cinema_adapter.py` | CineMA-to-CARE adapter |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/registration_model.py` | learned registration U-Net |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_dictionary.py` | eight-slot temporal dictionary |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_model.py` | temporal segmentation head |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_output.py` | real SyN helper and temporal output path |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/models/proposal_prototypes.py` | prototype bank and no-T2-safe negatives |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/models/srr_propref.py` | SRR proposal-refinement model |

The existing `docs/figures/round03_route_architecture/*` files were inspected. The older diagrams are kept for provenance, but the new model-focused D2 files are the source of truth for this repair.

## Diagram Legend

| Encoding | Meaning |
| --- | --- |
| Green solid | implemented and reviewer verified |
| Blue dashed | implemented or smoke evidenced, not formal runtime complete |
| Yellow dashed | planned, scaffolded, or not executed in Round03 |
| Red solid | blocked evidence boundary or adequate negative gate |
| Gray dashed | stale historical evidence |
| Purple dashed | blocked authority boundary |

## Route B Concrete Architecture

Route B Round03 has real code shape, but its verified Round03 evidence stops at the B3 anatomy gate.

MyoPS forward path in `RouteBRound03MyoPS.forward`:

1. Input is `x [B,3,Z,H,W]`, modality order `LGE,T2,C0`, plus explicit `availability [B,3]` and `anchor_logits [B,6,Z,H,W]`. Zero-filled image channels do not replace the availability tensor.
2. `stems` map each modality from one channel to 32 channels. `down` builds the pyramid `[32,64,128,256]`.
3. Each `ExpertScale` has 16 residual experts: four shared, two per modality-private family, and two per modality-pair interaction family.
4. The router input is fused features plus a 16-channel availability embedding, anchor context, and proposal context. Invalid expert families are masked by setting invalid logits to `-1e4`; Round03 code then uses `torch.softmax`. The diagram therefore marks entmax/top scheduling as SRR-v3 target status, not verified Round03 implementation.
5. The head path emits `anatomy_logits`, prototype-based `scar_proposal` and `edema_proposal`, `scar_roi` and T2-gated `edema_roi`, separate scar/edema residual refiners, a small composition gate, and `final_logits` built from anchor logits plus bounded residual deltas.
6. No-T2 edema safety is hard-wired: edema ROI and edema delta are multiplied by T2 availability, and `no_t2_edema_delta_abs_max` is checked.

Evidence hooks:

| Hook | Evidence |
| --- | --- |
| B2 final-output smoke | `gradient_intervention_report.csv` shows `myops_final_logits` changed with `changed_logit_l1=0.08683803677558899` |
| B2 CineMA smoke | `cinema_real_frame_smoke.json` records official logits shape `[1,4,192,192,16]` and the expected weight SHA |
| B2 registration/temporal smoke | `registration_temporal_smoke.json` records 7 registration integration steps and all temporal required fields |
| B3 formal gate | `completion.json` records 43003 optimizer steps, 1800.7964860140346 seconds, and 22 validation events |
| B3 failure | `gate_checks.anatomy_union_overfit=false` |
| B10 packet | `finalizer_state.json` has `ROUTE_B_ROUND03_TERMINAL_PACKET_READY_FOR_REVIEW` |
| review | `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE` |

The B3 loss in `train_myops.py` is `CE(final_logits) + 0.25*scar_proposal_BCE + 0.25*edema_proposal_BCE`. Pattern-SIP is present in the contract through `pattern_sip_coefficient` and the `pattern_sip_formula`, but B3 does not verify it as a final-output training objective.

## Route B Implemented vs Planned Gap

Route B Round03 should be read as a B3 adequate negative, not a full-route negative.

| Stage | Round03 status | Model implication |
| --- | --- | --- |
| B0 | present and reviewer accepted as part of terminal packet | source probe and manifest evidence exists |
| B1 | smoke/scaffold | model has four scales and 16 experts per scale |
| B2 | smoke/scaffold | forward, gradient, save/reload, export, CineMA, registration, and temporal shape gates passed |
| B3 | formal terminal evidence | training/accounting reached terminal status and failed the anatomy gate |
| B4 | not executed | OOF proposal training and shard discipline were not tested |
| B5 | not executed | separate scar/edema refiners were not formally trained |
| B6 | not executed | joint selector, same-split help/harm, and full final-output ablation were not tested |
| B7 | not executed | official CineMA matched random control did not run |
| B8 | not executed | faithful registration with case-level evidence did not run |
| B9 | not executed | registered temporal final-output rows did not run |
| B10 | verified accounting | packet is terminal and not monitor-only |

The failure reason is the B3 anatomy gate. It does not prove the proposal, refiner, selector, CineMA control, registration, or temporal modules are scientifically ineffective.

## Route C Concrete Architecture

Route C Round03 has a concrete MyoPS plus Cine evidence chain that the latest reviewer calls evidence-complete.

MyoPS R1:

1. `SRRProposeRefineMyoPS.forward` consumes MyoPS images, availability, anchor features, and component features.
2. `ProposalDictionary` combines positive similarity, negative similarity, negative memory, evidence logits, anatomy prior, anchor evidence, and component evidence.
3. `AnatomyDistanceROIPrior` builds `P_union`, `P_LV`, `P_RV`, distances, uncertainty, scar soft gate, and T2-gated edema soft gate.
4. `CropSoftROIRefinementHead` refines scar and edema logits inside local soft ROI crops and pastes bounded residuals back.
5. `BaselinePreservingResidualGate` and branch arbitration keep the final path explicit rather than hiding a silent anchor identity.

R1 final-output evidence:

| Evidence | Reviewer-supported result |
| --- | --- |
| `intervention_controls.csv` | 264 rows total |
| positive/negative prototype swap | 88/88 harmful known-bad rows; 88/88 changed logits; 88/88 changed voxels; 17633 changed voxels total; 80/88 changed components |
| no-op control | 88/88 zero-effect rows |
| anchor residual-off control | 88/88 zero-effect rows |
| `component_state_classification.csv` | D2 and D3 swap rows classify as `KNOWN_BAD_DETECTED_HARMFUL` with tensor, final-logit, and final-label changes |

Cine R2:

| Component | Evidence |
| --- | --- |
| official CineMA source | `mathpluscode/CineMA`, commit `c10daa1d93f0ea28d8b9ad9206b0f673d25805c1` |
| HF revision | `b1251ee50423bceeca84c080782fc3bc7756dea6` |
| weight SHA | `c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f` |
| license | MIT |
| outputs | real logits, probabilities, features, and entropy are retained as evidence |
| matched random control | same downstream contract with distinct pretrained/random source hashes |

Registration R3:

1. `RegistrationUNet` predicts a stationary velocity field.
2. `integrate_stationary_velocity` enforces seven scaling-and-squaring steps.
3. `jacobian_determinant` computes the true Jacobian determinant from central differences.
4. R3 includes 60 registration pair receipts, 12/12 case gates passing, inverse consistency evidence, and real ANTsPy SyN controls.

Temporal R3:

1. Temporal input consumes registered logits, registered features, uncertainty, velocity, displacement, Jacobian, motion, texture residual, frame quality, temporal position, and valid masks.
2. `TemporalSlotDictionary` has eight named slots: ED anatomy anchor, early/late systolic contraction, early/late diastolic relaxation, motion magnitude, registered texture residual, and registration uncertainty safety.
3. `CineTemporalModel` combines frame0 CineMA-adapter logits with temporal dictionary features through an ED-space head.
4. `temporal_final_output_interventions.csv` has 12 rows, all with changed logits, changed voxels, and changed components.

## Route C Evidence-Complete Chain

The latest Route C review emits `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`. It confirms:

| Route C claim | Current evidence state |
| --- | --- |
| R1 known-bad repair | verified harmful swap plus zero-effect controls |
| R1 validator repair | strict R1/R2/final validators and known-bad tests pass |
| R2 CineMA | real source, weight SHA, license, logits/probs/features/entropy, matched random control |
| R3 registration | learned SVF, seven-step integration, true Jacobian, real SyN, pair receipts, case gate |
| R3 temporal | registered evidence fields consumed with gradients and 12 final-output rows changed |

`/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/architecture_delta_final.md` is stale historical evidence. It says Route C still requires revision/evidence, but the latest independent reviewer supersedes it.

## Route B vs Route C Technical Gap

| Dimension | Route B Round03 | Route C Round03 |
| --- | --- | --- |
| Model potential | full SRR-v3 target with modality stems, experts, router, Pattern-SIP, proposal/refiner, Cine temporal target | full M10/Round03 burden retained through MyoPS interventions and Cine temporal chain |
| Actual evidence boundary | B3 anatomy gate failure; B4-B9 not executed | R1/R2/R3 evidence-complete by latest reviewer |
| Router/dictionary evidence | masked softmax router verified for invalid-slot zero; entmax/top target not verified | D2/D3 proposal dictionary interventions verified with final-output changes |
| Prototype evidence | deterministic/offline bank smoke; formal OOF B4 not executed | prototype swap known-bad changes logits/voxels/components |
| Final MyoPS output | B2 smoke final-logit change; no B6 formal final-output ablation | final logits and labels changed in R1 D2/D3 evidence |
| CineMA | official-source smoke only; matched random B7 not executed | official source and matched random control verified |
| Registration | SVF smoke only; B8 not executed | learned SVF, true Jacobian, real SyN, 60 pair receipts, 12/12 case gate |
| Temporal | required-field smoke only; B9 not executed | registered temporal evidence consumed; 12 final-output rows changed |
| Reviewer token | `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE` | `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE` |

## What the Diagrams Do NOT Authorize

The diagrams and CSV can be used as Round4 planner/controller/reviewer structural inputs. They do not authorize:

| Blocked action | Reason |
| --- | --- |
| validation packaging or upload | no user authorization and no route promotion |
| route promotion | reviewer tokens are not promotion tokens |
| hosted metric claim | no validation submission is represented here |
| final scientific decision | controller and reviewer boundaries remain blocked |
| M11 or cross-route merge | outside this audit scope |
| treating Route B as a full negative | Round03 stopped at B3 |
| treating stale Route C mapper text as current | latest reviewer supersedes it |

## Validation / Render Commands

Commands to validate this repair:

```bash
git fetch --all --prune
git branch --show-current
git rev-parse HEAD
git status --short --branch
d2 --version
d2 docs/figures/round03_route_architecture/round03_routeB_model_architecture.d2 docs/figures/round03_route_architecture/round03_routeB_model_architecture.svg
d2 docs/figures/round03_route_architecture/round03_routeB_implemented_vs_planned_model.d2 docs/figures/round03_route_architecture/round03_routeB_implemented_vs_planned_model.svg
d2 docs/figures/round03_route_architecture/round03_routeC_model_architecture.d2 docs/figures/round03_route_architecture/round03_routeC_model_architecture.svg
d2 docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.d2 docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.svg
rsvg-convert docs/figures/round03_route_architecture/round03_routeB_model_architecture.svg -o docs/figures/round03_route_architecture/round03_routeB_model_architecture.png
rsvg-convert docs/figures/round03_route_architecture/round03_routeB_implemented_vs_planned_model.svg -o docs/figures/round03_route_architecture/round03_routeB_implemented_vs_planned_model.png
rsvg-convert docs/figures/round03_route_architecture/round03_routeC_model_architecture.svg -o docs/figures/round03_route_architecture/round03_routeC_model_architecture.png
rsvg-convert docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.svg -o docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.png
ls -lh docs/figures/round03_route_architecture/
identify docs/figures/round03_route_architecture/round03_routeB_model_architecture.png
identify docs/figures/round03_route_architecture/round03_routeB_implemented_vs_planned_model.png
identify docs/figures/round03_route_architecture/round03_routeC_model_architecture.png
identify docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.png
git diff --check
```

D2 SVG rendering succeeded. D2 direct PNG rendering attempted but the local Playwright driver download returned 404, so PNG files were generated from SVG with `rsvg-convert`.

No training, Slurm, controller, reviewer, upload, raw data, checkpoint, or runtime-tree command is part of this validation.
