---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
planner_branch: main
planner_base_main: 7042135a4cc5be44b090fee93d4d1ee25b72fc0e
route_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
reviewer_token_inherited: ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE
status: DRAFT_FOR_ROUND04_CRITIC_REVIEW
controller_start_authorized: false
required_critic_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
controller_contract_path: prompts/routes/route_B_round04_controller_contract.md
executor_plan_path: prompts/routes/route_B_round04_executor_plan.yaml
critic_request_path: prompts/routes/route_B_round04_critic_request.md
planner_audit_path: prompts/routes/route_B_round04_planner_audit.md
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# CARE Route B Round04 Planner Plan

## 1. Planner decision

Round03 is a reviewed adequate negative at the B3 evidence-warmup gate, not a reviewed negative of the full Route B architecture. The evidence proves that the B3 run was long enough to interpret, that the repaired `E,E,S,R` sampler was real, and that the implementation did not fail through monitor, undertraining, stale accounting, or missing no-T2 safety. It does not test proposal training, refiner training, joint checkpoint selection, formal CineMA matched control, faithful registration, or registered temporal aggregation.

Round04 therefore preserves the complete four-scale SRR-v3 route and changes one scientific-control error in the Round03 contract: `anatomy_union_overfit` can no longer act alone as a route-global terminal negative before lesion formation and Cine fidelity are exercised. Round04 first repairs and validates the anatomy target and optimization path, then treats B3 as a representation-readiness stage. The first leaderboard-facing MyoPS scientific decision is moved to B6 after proposal, refiner, joint tuning, same-split evaluation, and real final-output interventions. The Cine branch becomes independent after the common implementation freeze, so a MyoPS representation-stage result cannot silently erase B7-B9.

This is not permission to bypass a failed implementation. The anatomy micro-overfit gate remains strict. A failure of the repaired two-case train-only micro-overfit is classified as an implementation or label-contract defect and returns `NEEDS_REVISION`; it is not converted into an adequate negative. A pass permits full-path training to continue even when the learned anatomy decoder needs anchor-assisted localization support, because anatomy is an auxiliary localization source rather than one of the three leaderboard outputs.

## 2. Route objective recovered from the Project diagrams

The visually read diagrams recover one continuous route objective:

- SRR-v2: use only observed LGE, C0, and T2 evidence; retrieve shared and modality-private representations; generate anatomy-guided scar and edema proposals; apply pathology-specific soft-ROI refiners; model cine through reference-space registration and temporal retrieval.
- SRR-v2.5: separate scar and edema proposal geometry and refiner geometry; preserve T2-conditioned edema supervision; keep containment soft rather than hard clipping.
- SRR-v3: retain the four-scale retrieval bank, add interaction experts and train/OOF prototype evidence, use nnU-Net outputs only as anchor/context/safety evidence, and compose a bounded final correction. The Cine route must consume official anatomy features, registration outputs, motion, uncertainty, and temporal position before producing `myocardium_cinemyops`.

The Round04 route is therefore availability-aware selective retrieval plus anatomy-guided lesion proposal plus pathology-specific soft-ROI refinement plus bounded final composition, with a faithful registered temporal Cine branch. It is not an nnU-Net-only route, a postprocess route, a wrapper route, a validator route, or a declaration-only route.

## 3. Current implementation audit

| Stage | What is currently implemented and evidenced | What is not implemented or not formally proved | Evidence paths on `origin/route_B` | Round03 reviewer interpretation |
|---|---|---|---|---|
| B0 | Canonical order `[LGE,T2,C0]`; four deterministic manifests; frozen sampler receipt; source probe; explicit rejection of legacy order and known-bad historical paths. | No Round04 anatomy-target audit, same-split baseline manifest, or Round04 code/config/split fingerprint exists. | `results/route_B/round03/executors/B0/completion.json`; `source_probe.json`; `manifest_freeze_receipt.json`; `configs/route_B_round03/manifests/*` | B0 evidence may be inherited only after a fresh fingerprint audit. |
| B1 | Route-local full-model scaffold under `src/care_myocardium/route_B_round03`; four scales `[32,64,128,256]`; sixteen experts per scale; four-shard OOF memory contract; official CineMA weight SHA; seven-step SVF interface; named registered temporal interface. | Static/scaffold evidence does not prove proposal, refiner, matched-random, registration, or temporal formal training. It also does not prove the anatomy target used by B3 is semantically and optimizationally suitable. | `results/route_B/round03/executors/B1/completion.json`; `implementation_snapshot.md`; `tensor_contract.json`; route-local source package | B1 implementation evidence is credible, but only a starting point for Round04 repair. |
| B2 | Real MyoPS final-logit intervention; invalid-slot maximum weight `0`; no-T2 edema delta `0`; exact save/reload; official CineMA logits `[1,4,192,192,16]`; real decoder feature hook; seven-step registration smoke; temporal interface with all named fields. | These are implementation/smoke gates, not formal matched-control, registration, or temporal runtime. Formal training was not submitted at B2, which is correct for an implementation gate. | `results/route_B/round03/executors/B2/completion.json`; `gradient_intervention_report.csv`; `save_reload_report.json`; `cinema_real_frame_smoke.json`; `registration_temporal_smoke.json` | B2 supports code readiness, not leaderboard evidence. |
| B3 | Formal evidence warmup reached `43003` optimizer steps, `1800.7964860140346` train-loop seconds, `22` validation events, finite decreasing loss, exact no-T2 zero, zero invalid routing, and exact `E,E,S,R` sampler counts. | `anatomy_union_overfit=false`; no proposal, refiner, joint selector, final full MyoPS ablation, or leaderboard-facing same-split comparison ran. | `results/route_B/round03/executors/B3/completion.json`; `training_adequacy.csv`; sampler receipts; runtime path recorded in the packet | This is an adequate negative for the Round03 B3 gate only. It is not a negative of B4-B9 or of the full route. |
| B4 | No formal Round03 packet. | OOF prototype fit tied to a selected parent checkpoint, hard-negative queue, scar proposal training, and T2-present edema proposal training are unexecuted. | Absence is recorded by B10. | Blocked by the old B3 contract. |
| B5 | No formal Round03 packet. | Scar small-ROI and edema large-ROI refiner training are unexecuted. | Absence is recorded by B10. | Blocked by the old B3 contract. |
| B6 | No formal Round03 packet. | Joint tuning, selected-checkpoint reload, 44-case same-split evaluation, case-wise help/harm, final-output intervention, and MyoPS ablation are unexecuted. | Absence is recorded by B10. | Blocked by the old B3 contract. |
| B7 | No formal Round03 packet. | Official CineMA pretrained versus matched-random runtime is unexecuted. | Absence is recorded by B10. | Blocked even though it is scientifically separable after the common implementation freeze. |
| B8 | No formal Round03 packet. | Learned seven-step SVF runtime, true Jacobian, inverse consistency, full denominators, real SyN control, and case-level aggregation are unexecuted. | Absence is recorded by B10. | Blocked by the old global progression rule. |
| B9 | No formal Round03 packet. | Registered temporal aggregation, full temporal ablation, cumulative resume, and final-output intervention are unexecuted. | Absence is recorded by B10. | Blocked by the old global progression rule. |
| B10 | Terminal accounting covered every started attempt with `afterany`; strict validator passed; heavy-artifact scan passed; no forbidden authority was exercised. | The packet is terminal only for Round03. It cannot authorize a Round04 controller. | `results/route_B/round03/executors/B10/completion.json`; `validator_packet_report.json`; `finalizer_state.json`; `routing_ledger.csv` | Reviewer emitted `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`. |

## 4. Why the old B3 gate is revised

The old gate mixed two questions:

1. Is the anatomy branch trainable and semantically wired correctly?
2. Has the complete lesion-formation system shown leaderboard-facing value?

`anatomy_union_overfit` is suitable for the first question only. It cannot answer the second because proposal, prototype discrimination, hard-negative replay, soft ROI, pathology-specific refinement, bounded composition, and all Cine stages had not run. Using it as a route-global scientific stop creates a false equivalence between an auxiliary localization optimization proxy and the complete SRR-v3 outcome.

Round04 separates the questions mechanically:

- B1/B2 require a repaired anatomy target and a strict two-case micro-overfit. Failure is an implementation/label defect.
- B3 requires adequate representation warmup, valid routing, exact no-T2 behavior, and usable localization support. B3 does not issue a final route-negative token.
- B4 and B5 must execute proposal and refiner training after B3 readiness.
- B6 is the first MyoPS stage allowed to classify the full route as candidate evidence or adequate negative evidence.
- B7-B9 form an independent Cine chain after B2 and cannot disappear because of a MyoPS auxiliary-stage metric.

## 5. Anatomy repair specification

### 5.1 Label semantics

The compact-label anatomy targets are frozen as:

```text
Y_union = 1[label in {1 myocardium, 4 edema, 5 scar}]
Y_LV    = 1[label == 2]
Y_RV    = 1[label == 3]
```

The validator must compare these masks against the official-value round trip and reject pure-myocardium-only union targets. Scar and edema replace myocardium in the compact label map; excluding them from `Y_union` makes a pathology-aware localization head internally contradictory.

### 5.2 Stable anatomy path without reducing SRR

At each scale, the anatomy decoder consumes both the routed anatomy representation and a masked-fused observed-modality lateral feature:

```text
a_l = Conv1x1(concat(routed_anatomy_l, masked_mean(valid_stem_features_l)))
```

The routed feature remains live, receives gradients, and has an intervention requirement. The lateral feature prevents the anatomy head from depending entirely on a sparse router before that router has stabilized. Proposal localization support is:

```text
p_support = max(p_learned_union, 0.5 * stop_gradient(p_anchor_union))
```

The anchor term is a bounded safety floor and is evaluated through an `anchor_support_floor_off` intervention. It is not the final segmentation base and cannot satisfy the SRR contribution gate by itself.

### 5.3 Train-only micro-overfit

B0 deterministically selects two complete tri-modal anatomy-positive training cases: the lexicographically first qualifying CenterB case and the lexicographically first qualifying CenterC case from the frozen 44-case manifest. Absence of either case is a manifest blocker.

B1 runs 2,000 optimizer steps, at least 600 train-loop seconds, and four evaluation events with pathology heads frozen. Passing values are:

- union Dice at least `0.90` on each case;
- mean LV/RV Dice at least `0.85` on each case;
- anatomy loss decreases by at least `70%` from the first 100-step median to the last 100-step median;
- routed-anatomy gradient norm and lateral-anatomy gradient norm are finite and greater than `1e-8`;
- save/reload maximum absolute output delta at most `1e-5`.

A miss after the fixed budget is `ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_NEEDS_REVISION`. It cannot be published as a scientific negative.

## 6. Full SRR-v3 implementation target

### 6.1 MyoPS

The Round04 MyoPS final path retains:

- three modality-specific stems in canonical order `[LGE,T2,C0]`;
- four scales with channels `[32,64,128,256]`;
- per-scale shared, LGE-private, T2-private, C0-private, LGE-T2, LGE-C0, and T2-C0 expert families;
- lesion- and spatial-conditioned pathology routers with availability masking and per-batch/task/scale/slot invalid-weight evidence;
- Pattern-SIP as an optimized group-conditioned loss, not a post-hoc alias;
- fold-safe four-shard train/OOF-fitted frozen prototype banks;
- training-only scar and edema hard-negative queues with no-T2 edema exclusion;
- learned union/LV/RV anatomy decoder with bounded anchor localization floor;
- separate scar and edema proposal heads;
- separate soft ROI geometry and separate refiners;
- bounded final correction with nonzero changed-logit, changed-voxel, and changed-component receipts;
- official six-label reconstruction, save/reload, and export QA.

### 6.2 Cine

The Round04 Cine final path retains:

- pinned official CineMA pretrained weights and source SHA;
- an architecturally matched random-init source with identical downstream initialization, cases, frames, optimizer, augmentation draws, cadence, and selector;
- official multiclass logits, decoder features, probabilities, and uncertainty;
- ED/reference and key-frame provenance;
- learned symmetric stationary velocity with seven scaling-and-squaring steps;
- true voxel-coordinate Jacobian, folding rate, inverse consistency, and full registration loss;
- real SyN control on the same pairs;
- case-level registration aggregation with full denominators;
- registered temporal inputs containing logits, features, anatomy, uncertainty, velocity, integrated displacement, Jacobian, motion magnitude, texture residual, frame quality, temporal position, and valid-frame mask;
- registered temporal aggregation and a full reference/unregistered/registered/component-off/matched-random ablation;
- cumulative resume with parent hashes and zero credit for failed, timed-out, preempted, partial, reset, gap, overlap, or duplicate attempts.

## 7. Stage graph and continuation policy

```text
B0 evidence/fingerprint/manifest rebind
  -> B1 anatomy target and optimization repair
  -> B2 full implementation and regression freeze
       -> B3 MyoPS representation warmup
            -> B4 OOF bank + proposal training
                 -> B5 pathology-specific refiner training
                      -> B6 joint tuning + selector + full MyoPS ablation
       -> B7 official CineMA pretrained/matched-random formal runtime
            -> B8 learned SVF + real SyN formal runtime
                 -> B9 registered temporal training + full Cine ablation
  -> B10 afterany terminal accounting, aggregation, completion check, review request
```

B3 and B7 are isolated parallel lanes after B2. B4/B5/B6 and B8/B9 remain sequential within their own lane.

### 7.1 B3 continuation classes

B3 always records one of two localization modes after adequate runtime:

- `LEARNED_ANATOMY_PRIMARY`: learned union median Dice at least `0.65`, positive-case nonempty rate at least `0.90`, median volume ratio in `[0.25,4.0]`, and learned HD95 no worse than anchor by more than `5 mm`.
- `ANCHOR_ASSISTED_ANATOMY_SUPPORT`: the B1 micro-overfit remains passed, learned union is finite and nonconstant, `p_support` covers at least `95%` of scar and T2-present edema GT voxels on the train-only diagnostic subset, and the learned-anatomy on/off intervention changes proposal input tensors. This mode is a risk classification, not a candidate claim.

If neither class holds, B3 returns `NEEDS_REVISION`. If either class holds and all adequacy/routing/safety gates pass, B4 proceeds. B3 cannot emit a full-route adequate-negative token.

### 7.2 B4 continuation classes

B4 records learned proposal strength but does not erase B5:

- `PROPOSAL_STRONG`: scar-positive lesion recall at least `0.85`; T2-present edema-positive lesion recall at least `0.90`; soft-ROI voxel coverage at least `0.90` for scar and `0.95` for edema; median ROI volume ratio in `[0.25,4.0]`.
- `PROPOSAL_WEAK_WITH_CONSERVATIVE_ROI`: OOF provenance and gradients pass, learned proposal is nonconstant, and the fixed anatomy-neighborhood floor preserves the same voxel-coverage floors. B5 trains both the full path and the conservative-ROI control.

Invalid OOF provenance, unsafe edema negatives, disconnected similarities, or failed implementation validation block B5. A weak but valid proposal does not create an early route-negative packet.

### 7.3 B8 registration continuation classes

- Learned SVF is the primary temporal registration source when at least `90%` of the 12 cases pass the fixed case-level gate.
- When learned SVF misses that gate but real SyN meets it, B9 proceeds with SyN-registered evidence as the primary registered lane and retains learned SVF as adequate-negative registration evidence.
- When neither source meets the case-level gate, B9 cannot claim registered temporal evidence; B10 records `CINE_REGISTRATION_BLOCKER` for independent review.

## 8. Minimum effective training

| Stage | Optimizer steps | Train-loop seconds | Validation events | Full-case events | Cases | Scientific role |
|---|---:|---:|---:|---:|---:|---|
| B1 anatomy micro-overfit | 2,000 | 600 | 4 | 4 | 2 train-only cases | Implementation/label gate |
| B3 evidence warmup | 6,000 | 1,800 | 3 | 1 | 44 evaluation manifest | Representation readiness |
| B4 proposal | 8,000 | 2,400 | 4 | 2 | 44 evaluation manifest | Lesion proposal evidence |
| B5 refiner | 10,000 | 3,000 | 5 | 3 | 44 evaluation manifest | Lesion refinement evidence |
| B6 joint | 8,000 | 2,400 | 4 | 4 | 44 evaluation manifest | MyoPS terminal science packet |
| B7 pretrained lane | 8,000 | 3,600 | 4 | 4 | 12 cine cases | CineMA formal control |
| B7 random lane | 8,000 | 3,600 | 4 | 4 | 12 cine cases | Matched random control |
| B8 registration | 25,000 | 7,200 | 10 | 4 | 12 cases, at least 60 pairs | Registration fidelity |
| B9 temporal | 20,000 cumulative | 7,200 | 10 | 4 | 12 cine cases | Cine terminal science packet |

Every stage also requires prediction sanity, loss decrease, selected-checkpoint clean reload, cache isolation, source/config/split/case/label/preprocess/decode hashes, and post-completion aggregation.

## 9. Same-split evaluation and leaderboard-facing outputs

B0 freezes a same-split nnU-Net baseline receipt. B6 and B9 reuse the exact case lists, label mapping, evaluator, and decode rules.

Required MyoPS outputs:

```text
results/route_B/round04/executors/B6/myops_metrics_casewise.csv
results/route_B/round04/executors/B6/myops_help_harm_matrix.csv
results/route_B/round04/executors/B6/myops_subgroup_summary.csv
results/route_B/round04/executors/B6/myops_ablation_matrix.csv
results/route_B/round04/executors/B6/final_output_interventions.csv
results/route_B/round04/executors/B6/checkpoint_selector.json
```

Required Cine outputs:

```text
results/route_B/round04/executors/B9/cine_metrics_casewise.csv
results/route_B/round04/executors/B9/cine_help_harm_matrix.csv
results/route_B/round04/executors/B9/cine_ablation_matrix.csv
results/route_B/round04/executors/B9/temporal_final_output_interventions.csv
results/route_B/round04/executors/B9/checkpoint_selector.json
```

Every case-wise row includes baseline and Route B values for Dice, HD95, remote-FP volume, component count, volume ratio, nonempty status, changed voxels, changed components, and subgroup flags. Scar rows identify scar-positive cases. Edema scientific rows identify T2-present edema-positive cases. No-T2 rows measure safety only. CenterB and CenterC are reported separately. Both-empty pathology rows are excluded from improvement means and never count as help.

## 10. Full ablation matrix

MyoPS uses the same selected checkpoint, cases, evaluator, and decode rule for:

1. same-split nnU-Net anchor;
2. full SRR-v3;
3. learned anatomy signal off;
4. anchor localization floor off;
5. prototype similarity off;
6. hard-negative refresh off;
7. interaction experts off;
8. Pattern-SIP off;
9. proposal node off;
10. scar refiner off;
11. edema refiner off;
12. both refiners off;
13. bounded final correction off;
14. nnU-Net context off.

Cine uses the same selected downstream checkpoint, cases, frames, and decode rule for:

1. pretrained reference-only;
2. pretrained unregistered multi-frame;
3. pretrained registered temporal full;
4. temporal router off;
5. motion/Jacobian evidence off;
6. anatomy evidence off;
7. uncertainty/quality evidence off;
8. matched-random registered temporal;
9. learned-SVF registration;
10. real-SyN registration.

A file named `ablation` must contain real node interventions and final-output deltas. Summary-only tables must use a summary name.

## 11. Evidence-complete and adequate-negative classification

MyoPS target gates:

- `myops_scar`: scar-positive Dice delta at least `0.01` or HD95 improvement at least `1 mm`, with remote-FP nonincrease and severe-harm fraction at most `0.20`.
- `myops_edema`: T2-present edema-positive Dice delta at least `0.02` or HD95 improvement at least `1 mm`, with exact no-T2 Route-B-owned edema change equal to zero.

Cine target gate:

- `myocardium_cinemyops`: registered temporal Dice delta versus reference-only at least `0.01`, HD95 disadvantage at most `1 mm`, and final-label change on at least eight cases.

A reviewer may classify evidence complete with candidate signal only when all implementation, provenance, adequacy, safety, finalizer, and validator gates pass; at least two target gates are positive; the third target is non-worse; MyoPS has nonzero changed voxels/components/cases; and Cine has nonzero registered temporal final-output effects.

A reviewer may classify an adequate negative only after B6 and B9 have terminal adequate evidence or after a faithful B8 registration blocker is fully accounted and prevents B9. An auxiliary-stage metric alone cannot establish the adequate-negative classification for the whole route.

## 12. Deep-research mapping

| Research requirement | Target code/module | Stage | Required evidence | Validator decision |
|---|---|---|---|---|
| Canonical observed-modality order and no zero filling | `src/care_myocardium/route_B_round04/myops/input_contract.py` | B0-B2 | modality-order receipt; missing-modality tensor and gradient tests | wrong order or nonzero missing path fails |
| Four-scale shared/private/interaction retrieval | `myops/expert_bank.py`, `myops/router.py` | B1-B3 | per-batch/task/scale/slot weights and gradients | disconnected family or invalid weight above `1e-8` fails |
| Group-conditioned Pattern-SIP | `myops/pattern_sip.py` | B1-B3/B6 | loss tensor, coefficient schedule, group usage, gradient, on/off final effect | alias or report-only path fails |
| Correct anatomy union and stable localization | `myops/anatomy.py`, `myops/targets.py` | B1-B3 | label round trip; two-case overfit; learned/anchor support interventions | pure-myocardium target or failed micro-overfit fails |
| Train/OOF prototype provenance | `myops/prototype_bank.py` | B4 | shard membership, source manifest, checkpoint SHA, tensor SHA, leakage audit | bootstrap, EMA inference, current-case, validation, or test leakage fails |
| Safe hard-negative replay | `myops/hard_negative.py` | B4-B5 | source classes, queue ledger, before/after proposal and final metrics | no-T2 myocardium in edema queue fails |
| Scar and edema proposals | `myops/proposal.py` | B4/B6 | lesion recall, voxel coverage, similarity contribution, final-output intervention | constant/disconnected proposal fails |
| Pathology-specific soft ROI and refiners | `myops/soft_roi.py`, `myops/refiner.py` | B5/B6 | ROI coverage, retention, refiner on/off final metrics | hard deletion, shared undifferentiated head, or zero effect fails |
| Bounded final correction | `myops/composition.py` | B5-B6 | gate/delta bounds, changed logits/voxels/components, no-T2 exact zero | identity-only or unbounded correction fails |
| Same-split baseline and lesion-centric evaluation | `evaluation/myops_eval.py`, `evaluation/selector.py` | B0/B6 | baseline hash; case-wise help/harm; subgroups; fresh predictions | missing baseline or proxy-only metric fails |
| Official CineMA source | `cine/cinema_source.py` | B1-B2/B7 | license, source commit, weight SHA, logits/features/uncertainty, clean reload | fake source, wrong SHA, or wrapper-only source fails |
| Matched random control | `cine/matched_control.py` | B7 | parameter-shape and downstream-state equality; source-init-only difference | unmatched architecture/data/optimizer fails |
| Seven-step SVF and real SyN | `cine/svf_registration.py`, `cine/syn_control.py` | B8 | velocity, integrated fields, true Jacobian, inverse composition, per-pair and per-case receipts | direct displacement, proxy Jacobian, copied SyN, or pair-as-case fails |
| Registered temporal aggregation | `cine/temporal.py` | B9 | named input consumption, cumulative resume, interventions, full ablation | frame0 fallback, unregistered primary, reset/gap/overlap fails |
| Official label/export semantics | `export/label_map.py`, `export/roundtrip.py` | B2/B6/B9 | compact-to-official round trip and shape/affine checks | silent relabeling or compact proxy as official fails |

## 13. Slurm and terminal-accounting contract

- Formal wrappers use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python` after a compute-node preflight that prints executable, Python version, torch version, CUDA visibility, config hash, split hash, code hash, and writable roots.
- Long-wait compatible work races `htzhulab` and `a100-gpu` with identical scientific hashes, isolated attempt roots, one atomic winner lock, pending-loser cancellation, loser zero credit, and full attempt accounting.
- `volta-gpu` is used only for executors whose unchanged scientific configuration passes a peak-memory ceiling of `14.5 GiB`. Failure of that preflight disables the V100 attempt without changing model, batch semantics, loss, split, label map, or budget.
- Training-to-training dependencies use `afterok`. B10 uses `afterany` over every started attempt.
- Submitted, pending, running, monitor, awaiting-accounting, timed-out, failed startup, preempted, or partial packets are not completion.
- The controller remains responsible through terminal `sacct`, aggregation, strict validation, mapper final, completion check, review request, and a lightweight local packet commit. The controller and runtime roles do not push.

## 14. Required critic decision

A separate Route B Round04 critic must review the exact main commit containing these six planning files. The critic must verify deep-research coverage, the scientific justification for the B3 revision, the absence of controller design gaps, the completeness of the B0-B10 terminal graph, the same-split and subgroup contracts, the formal Cine chain, the Slurm race/finalizer semantics, and the known-bad validator matrix.

Only `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` bound to the exact planning commit permits controller start. Planner publication and push do not provide that permission.

## 15. Authority boundary

This plan does not authorize validation packaging or upload, route promotion, M11, hosted metric claims, cross-route merge, or a final scientific decision. It also does not perform code changes, model training, Slurm submission, runtime review, or reviewer work.
