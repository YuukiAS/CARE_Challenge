# Round03 Route B / Route C Aligned Model Architecture Audit

## Scope / Non-Authority Boundary

This repair replaces the previous status-heavy diagrams with aligned model architecture diagrams. Route B and Route C now use the same six-panel visual template, same left-to-right direction, same status legend, and same stage slots so a reviewer can compare corresponding model components directly.

This audit is read-only with respect to route execution. It did not train, submit Slurm jobs, start a controller or reviewer, package or upload validation, promote any route, start M11, claim hosted metrics, or make a final scientific decision.

Active repository: `/users/a/e/aereinh/CARE`.

Current main at audit start: `64f5a27298cb2efd1f576a70296e49388ab0b717`, branch `main`, clean and equal to `origin/main`.

## Source Files and Evidence Inspected

Route B source files and evidence:

| Path | Use |
| --- | --- |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/model.py` | MyoPS stems, pyramid, ExpertScale router, prototype bank, proposal/refiner/final composition |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/contract.py` | modality order `[LGE,T2,C0]`, `SCALES=(32,64,128,256)`, `EXPERTS_PER_SCALE=16`, Pattern-SIP target contract |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/cinema.py` | CineMA adapter and matched random source scaffold |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/registration.py` | SVF registration scaffold and seven-step integration |
| `/users/a/e/aereinh/CARE_worktrees/route_B/src/care_myocardium/route_B_round03/temporal.py` | registered temporal evidence consumer and 8 learned slots |
| `/users/a/e/aereinh/CARE_worktrees/route_B/scripts/route_B_round03/run_implementation_gate.py` | B2 smoke gates |
| `/users/a/e/aereinh/CARE_worktrees/route_B/scripts/training/route_B_round03/train_myops.py` | B3-B6 stages and B3 gate logic |
| `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/review.md` | latest reviewer token and boundary |
| `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/controller_report.md` | controller terminal accounting |
| `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/round03/` | lightweight B0-B3/B10 evidence inventory |

Route C source files and evidence:

| Path | Use |
| --- | --- |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/models/srr_propref.py` | SRR propose-refine trunk, proposal dictionaries, ROI prior, crop refiners, final logits/labels |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/models/proposal_prototypes.py` | prototype bank and T2-safe edema negatives |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/route_C/myops/evidence_contract.py` | fail-closed R1 evidence contract |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/route_C/cine/fidelity.py` | official CineMA provenance, SVF integration, true Jacobian, temporal adapter |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/cinema_adapter.py` | CineMA adapter over image plus prior |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/registration_model.py` | RegistrationUNet encoder/decoder and SVF output |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_dictionary.py` | 8-slot temporal dictionary |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_model.py` | CineTemporalModel final temporal head |
| `/users/a/e/aereinh/CARE_worktrees/route_C/src/care_myocardium/cine/temporal_output.py` | real ANTsPy SyN helper |
| `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/review.md` | latest reviewer token and evidence-complete judgment |
| `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/controller_report.md` | repaired blocker and validator accounting |
| `/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/round03/` | R1/R2/R3 lightweight evidence inventory |

## Aligned Diagram Template

All revised D2 diagrams use the same six panel slots:

| Panel | Comparison slot |
| --- | --- |
| Panel 1 | Inputs |
| Panel 2 | Trunk / Encoder |
| Panel 3 | Routing / Proposal / Prototype |
| Panel 4 | ROI / Refinement / Composition |
| Panel 5 | CineMA / Registration / Temporal |
| Panel 6 | Final Output Evidence / Review Boundary |

Status encoding is shared across Route B and Route C:

| Encoding | Meaning |
| --- | --- |
| green solid | implemented plus reviewer verified final-path evidence |
| blue dashed | implemented or smoke evidenced, not formal runtime complete |
| yellow dashed | planned, scaffolded, or not executed in Round03 |
| red solid | blocker, failed gate, or adequate negative boundary |
| gray dashed | stale historical evidence |
| purple dashed | authority boundary |

The main comparison figure is `/users/a/e/aereinh/CARE/docs/figures/round03_route_architecture/round03_routeB_routeC_aligned_network_comparison.png`.

## Route B Concrete Architecture

Route B Round03 code implements a real SRR-v3-shaped MyoPS path, but reviewer-confirmed formal evidence stops at B3.

The model path is:

| Panel | Route B model detail |
| --- | --- |
| Inputs | `x [B,3,Z,H,W]`, modality order `[LGE,T2,C0]`, explicit `availability [B,3]`, and `anchor_logits [B,6,Z,H,W]`. Zero-filled channel values are not treated as availability. |
| Trunk / Encoder | Three modality stems, each `Conv3d(1,32)`, followed by pyramid channels `[32,64,128,256]` and one `ExpertScale` at each scale. |
| Routing / Proposal / Prototype | `ExpertScale.forward` uses 16 experts per scale: shared, modality-private, and modality-pair families. Invalid expert families are masked to `-1e4` and then routed with `torch.softmax`. `OfflinePrototypeBank` contributes scar/edema positive-negative similarity maps. |
| ROI / Refinement / Composition | `anatomy_head` emits 4 anatomy logits. `scar_proposal` and T2-gated `edema_proposal` define ROI masks. `scar_refiner` and `edema_refiner` emit bounded residual deltas, composed with a `12->16->1` gate into `final_logits [B,6,Z,H,W]`. |
| CineMA / Registration / Temporal | CineMA, SVF registration, and temporal consumer code exists and has B2 smoke evidence, but B7-B9 formal runtime stages were not executed. |
| Final Evidence / Review | B3 ran 43003 optimizer steps, 1800.8 seconds, and 22 validation events, then failed `anatomy_union_overfit=false`. Latest reviewer token is `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`. |

Two details are intentionally marked as not verified implementation: entmax/top scheduling and Pattern-SIP final-path training. `contract.py` records the Pattern-SIP target formula, but `train_myops.py` B3 uses `CE(final_logits) + 0.25*scar_proposal_BCE + 0.25*edema_proposal_BCE`. The Round03 router code uses masked softmax, not entmax.

## Route B Implemented vs Planned Gap

Route B is not a full route negative. The supported conclusion is narrower: B3 produced an adequate negative at the anatomy repair gate.

| Stage | Status in aligned diagrams | Interpretation |
| --- | --- | --- |
| B0-B2 | blue dashed smoke/implementation | code and smoke evidence exist for MyoPS forward, final-logit change, CineMA shape, registration shape, and temporal required fields |
| B3 | red solid blocker | formal warmup reached runtime/accounting minima and failed `anatomy_union_overfit` |
| B4-B6 | yellow dashed not executed | OOF proposal training, refiners, selector/joint final ablation were not tested |
| B7-B9 | yellow dashed not executed | matched random CineMA control, formal registration, and registered temporal final-output rows were not tested |
| B10/review | red solid adequate negative | terminal packet is reviewable as B3 adequate negative only |

## Route C Concrete Architecture

Route C Round03 is represented in the same six panel slots rather than as a separate evidence-chain graphic.

| Panel | Route C model detail |
| --- | --- |
| Inputs | MyoPS volumes, availability/T2 flag, anchor features, component features, cine frames, ED image/prior, and registered temporal evidence tensors. The exact Route C MyoPS shape is not fixed in the code as `[B,3,Z,H,W]`; the diagram marks this as `shape not explicit in code`. |
| Trunk / Encoder | `SRRProposeRefineMyoPS` runs modality encoder/retrieval, optional M10 two-pass spatial dictionary, and scar/edema decoders. Cine uses `CineMAAdapter`. Registration uses `RegistrationUNet` with `enc1/enc2/enc3/bottleneck`, up blocks, dec blocks, and a velocity head. |
| Routing / Proposal / Prototype | `PrototypeBank` and `ProposalDictionary` provide positive/negative prototype scoring, negative memory, evidence logits, anatomy prior, anchor evidence, and component evidence. |
| ROI / Refinement / Composition | `AnatomyDistanceROIPrior` builds `P_union/P_LV/P_RV`, distances, uncertainty, and scar/edema gates. `CropSoftROIRefinementHead` refines scar/edema crops. Baseline-preserving and branch arbitration gates produce final logits and labels. |
| CineMA / Registration / Temporal | R2 verifies official CineMA provenance and matched random control. R3 verifies learned SVF, seven-step scaling/squaring, displacement/warp, true Jacobian, real SyN control, 8-slot temporal dictionary, and `CineTemporalModel` final head. |
| Final Evidence / Review | R1 prototype swap changes final outputs while no-op and residual-off controls remain zero-effect. R3 has 60 registration receipts and 12 temporal final-output rows changing logits/voxels/components. Latest reviewer token is `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`. |

The external CineMA ConvUNetR depth is not introspected in the repository. The diagrams therefore identify the official source/provenance and adapter outputs without pretending the external backbone internals are locally expanded.

## Route C Evidence-Complete Chain

The latest reviewer file is authoritative for Route C Round03. It confirms:

| Evidence hook | Reviewer-confirmed result |
| --- | --- |
| R1 positive/negative prototype swap | 88/88 rows pass as harmful known-bad, 88/88 changed logits, 88/88 changed voxels, 80/88 changed components |
| R1 no-op and anchor residual-off controls | both controls have 88/88 zero-effect rows |
| R2 CineMA | official source, commit, HF revision, weight SHA, MIT license, logits/probs/features/entropy, and matched random control are real evidence rather than proxy-only future work |
| R3 registration | learned SVF, seven-step integration, true Jacobian, inverse consistency, real SyN, 60 pair receipts, and 12/12 case gate PASS |
| R3 temporal | registered logits/features/uncertainty, velocity, displacement, Jacobian, motion, texture residual, frame quality, temporal position, and valid masks are consumed; 12 final-output rows changed logits/voxels/components |

`/users/a/e/aereinh/CARE_worktrees/route_C/results/route_C/architecture_delta_final.md` is stale historical evidence. It conflicts with the latest repaired reviewer decision and is marked gray/stale in the diagrams.

## Route B vs Route C Technical Gap

| Same slot | Route B Round03 | Route C Round03 |
| --- | --- | --- |
| Inputs | fixed MyoPS `[B,3,Z,H,W]` and availability semantics | MyoPS plus cine/registered temporal evidence; MyoPS shape not explicit in code |
| Trunk / Encoder | modality stems, pyramid, 16-expert scales implemented; evidence only through B3 boundary | SRR propose-refine, Cine adapter, RegistrationUNet, temporal dictionary all reviewer verified |
| Routing / Proposal / Prototype | masked softmax router and prototype bank have smoke/B3 evidence; Pattern-SIP and OOF remain target/not executed | prototype/proposal path has known-bad swap and zero-effect controls with final-output effects |
| ROI / Refinement / Composition | anatomy gate failed; refiners and bounded composition are code/smoke, not B6 formal evidence | ROI prior, crop refiners, residual/arbitration gates have reviewed final logits/labels changes |
| CineMA / Registration / Temporal | CineMA/register/temporal shape smoke only; B7-B9 not run | official CineMA, matched random, real registration, true Jacobian, SyN, temporal final-output rows verified |
| Final Evidence / Review | `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`; B3 adequate negative only | `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`; evidence-complete packet only |

## What the Diagrams Do NOT Authorize

The diagrams and CSV are suitable as structure/evidence input for a Round4 planner, controller, or reviewer. They do not authorize validation upload, route promotion, hosted metric claims, M11, cross-route merge, final scientific decision, or treating reviewer evidence-complete as scientific victory.

They also do not authorize treating Route B as a full scientific negative. The downstream Route B modules remain unjudged because B4-B9 were not executed after the B3 anatomy gate failed.

## Validation / Render Commands

Commands run or intended for this local repair:

```bash
git fetch --all --prune
git branch --show-current
git rev-parse HEAD
git status --short --branch
d2 --version
d2 docs/figures/round03_route_architecture/round03_routeB_routeC_aligned_network_comparison.d2 docs/figures/round03_route_architecture/round03_routeB_routeC_aligned_network_comparison.svg
d2 docs/figures/round03_route_architecture/round03_routeB_model_architecture.d2 docs/figures/round03_route_architecture/round03_routeB_model_architecture.svg
d2 docs/figures/round03_route_architecture/round03_routeC_model_architecture.d2 docs/figures/round03_route_architecture/round03_routeC_model_architecture.svg
d2 docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.d2 docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.svg
rsvg-convert docs/figures/round03_route_architecture/round03_routeB_routeC_aligned_network_comparison.svg -o docs/figures/round03_route_architecture/round03_routeB_routeC_aligned_network_comparison.png
rsvg-convert docs/figures/round03_route_architecture/round03_routeB_model_architecture.svg -o docs/figures/round03_route_architecture/round03_routeB_model_architecture.png
rsvg-convert docs/figures/round03_route_architecture/round03_routeC_model_architecture.svg -o docs/figures/round03_route_architecture/round03_routeC_model_architecture.png
rsvg-convert docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.svg -o docs/figures/round03_route_architecture/round03_routeB_vs_routeC_model_gap.png
file docs/figures/round03_route_architecture/*.png
ls -lh docs/figures/round03_route_architecture/
identify docs/figures/round03_route_architecture/*.png
git diff --check
```

No route tests were run because this task only changes documentation, D2 diagram sources, and rendered figure artifacts. No training, controller, reviewer, Slurm, validation upload, raw data, checkpoint, or runtime tree was touched.
