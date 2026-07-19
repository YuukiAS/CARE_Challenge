---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: portfolio_planner_revision
planner_branch: main
planner_base_main: 30098813522cecd98e60bcb99e2676b28c1a5461
revision_source_critic_commit: 30098813522cecd98e60bcb99e2676b28c1a5461
revision_source_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
route_B_evidence_ref: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_review_commit: 17062b00edc3443aacefe8583568797a9f2655ba
route_C_reviewed_controller_commit: 1e663cfa64f00413f005bef26310290fd43ec8ab
route_C_review_token: ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE
status: REVISION_PENDING_COORDINATOR_RECEIPT_AND_CRITIC_REREVIEW
controller_start_authorized: false
required_coordinator_receipt: prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
required_critic_output: prompts/routes/route_B_round04_critic_rereview.md
required_critic_token: ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
---

# CARE Route B Round04 planner revision after Route C review and Route B critic

## 1. Portfolio decision

Route C Round03 has completed its controller task and its independent reviewer has accepted the repaired packet with `ROUTE_C_ROUND03_REVIEW_EVIDENCE_COMPLETE`. The former `positive_negative_prototype_swap` validator fail-open is closed: the repaired swap is detected as harmful, the no-op controls remain zero-effect, strict R1/R2/final validators pass, and the known-bad pytest suite passes. Route C is now `EVIDENCE_COMPLETE_FOR_PORTFOLIO_RECONCILIATION`. It is not sent to another reviewer unless a later Route C commit changes the reviewed packet or otherwise makes the reviewer binding stale.

Route B Round04 remains planning-only. The independent planning critic accepted the scientific design without downgrade but returned `ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION` for four mechanical blockers:

1. `CURRENT.md` remained on Round03.
2. B10 required successful B6/B9 merge receipts and was unreachable after authorized early terminal classes.
3. B0-B10 did not bind exact per-stage strict validator commands and exact known-bad failure keys.
4. No current exit-zero coordinator receipt existed for the final planning commit.

This revision closes the first three blockers in repository planning. The fourth remains deliberately pending: a Codex coordinator must execute the declared commands on the final `origin/main` commit in `/users/a/e/aereinh/CARE`, fill the coordinator receipt with exit-zero evidence, and only then request a new independent Route B planning critic review.

No controller is authorized by this publication.

## 2. Route objective recovered from SRR-v2, SRR-v2.5 and SRR-v3

The diagrams define one continuous Route B objective:

```text
observed LGE/T2/C0 with explicit availability
-> four-scale modality-specific stems and encoders
-> shared/private/interaction representation retrieval
-> learned anatomy support plus train/OOF frozen prototypes
-> scar and edema proposals with safe hard negatives
-> separate pathology-specific soft ROIs and refiners
-> bounded final correction over an nnU-Net anchor/context/safety source
-> official-label reconstruction and real final-output interventions
```

The Cine lane is equally mandatory:

```text
official CineMA pretrained and architecture-matched random source
-> per-frame multiclass logits/features/uncertainty
-> ED/reference and fixed key-frame provenance
-> seven-step SVF plus real SyN control
-> registered anatomy/features/motion/Jacobian/quality
-> registered temporal aggregation
-> case-wise controls, ablations and ED-space final output
```

Route B is not Route A, nnU-Net-only, postprocess-only, wrapper-only, validator-only, or declaration-only.

## 3. Frozen interpretation of Round03 Route B

Round03 B3 reached `43003` optimizer steps, `1800.7964860140346` train-loop seconds and `22` validation events after the `E,E,S,R` sampler repair. It passed finite loss, loss decrease, exact sampler counts/sequence, invalid-slot zero and no-T2 edema zero, but failed `anatomy_union_overfit`.

That is a reviewed adequate negative for the old B3 gate only. B4 proposal, B5 refiner, B6 joint selector, B7 CineMA matched control, B8 faithful registration and B9 registered temporal runtime did not execute. Therefore:

- B1 keeps a strict repaired anatomy micro-overfit implementation/label gate.
- B3 is representation readiness and cannot issue a full-route adequate-negative token.
- A valid B3 must continue to B4.
- A valid but weak B4 must continue to B5 through the conservative-ROI control.
- A faithful but weak B5 must continue to B6.
- B6 is the first MyoPS full-route scientific classification stage.
- B7-B9 start after B2 independently of B3 and independently of Route C completion.
- Route C evidence completeness does not remove or substitute Route B Cine work.

## 4. Scientific contract retained without reduction

### 4.1 MyoPS architecture

The canonical order is `[LGE,T2,C0]`; availability is explicit and unavailable modalities are masked before/after stems and in every private/interaction route. Four scales use channels `[32,64,128,256]`. Every scale has sixteen experts: four shared, two each for LGE/T2/C0 private evidence, and two each for LGE-T2, LGE-C0 and T2-C0 interactions.

Anatomy, scar and edema use pathology/spatial-conditioned two-pass entmax routing. Invalid logits are `-1e4` and maximum invalid absolute weight is `1e-8`. Pattern-SIP remains an optimized group-conditioned objective with family target mass `.50/.35/.15`, shared/private/interaction coverage floors `.60/.25/.20`, and the original coefficient schedule.

The anatomy target is:

```text
Y_union = 1[compact label in {1 myocardium, 4 edema, 5 scar}]
Y_LV    = 1[compact label == 2]
Y_RV    = 1[compact label == 3]
```

The learned anatomy path stays live. A bounded stop-gradient anchor union floor may support localization, but it cannot become the final-output base or satisfy the learned-anatomy intervention.

Formal prototypes remain four-shard, fold-safe, train/OOF-fitted, inference-frozen and serialized with source/checkpoint/split/tensor hashes. Bootstrap or online EMA memory cannot enter formal inference. The training-only hard-negative queue holds 256 component centroids per pathology per scale. No-T2 myocardium or unknown edema-status tissue cannot enter the edema queue.

Scar and edema have separate proposals, soft ROI geometry and refiners. Scar is LGE-dominant, focal and remote-FP sensitive. Edema is T2-conditioned, larger-context and recall sensitive. No-T2 edema loss, prototype/queue update, proposal, ROI, refiner, gate, delta and Route-B-owned output change are exactly zero.

Final correction remains bounded:

```text
delta_p   = 4.0 * tanh(refiner_logit_p - anchor_logit_p)
z_final_p = z_anchor_p + roi_p * gate_p * delta_p
```

### 4.2 Cine architecture

The official source remains pinned to:

```text
repository: mathpluscode/CineMA
code commit: c10daa1d93f0ea28d8b9ad9206b0f673d25805c1
Hugging Face revision: b1251ee50423bceeca84c080782fc3bc7756dea6
weight: finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors
weight SHA256: c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f
model: cinema.segmentation.convunetr.ConvUNetR
license: MIT
```

Pretrained and random lanes have identical architecture, parameter names/shapes, cases, frames, augmentation draws, optimizer, schedule, downstream initialization, cadence, selector and decode. Only source initialization differs.

The registration network emits stationary velocity and integrates forward/inverse transforms with exactly seven scaling-and-squaring steps. The packet must contain true voxel-coordinate Jacobian, folding rate, inverse-composition error, full registration loss, independently generated real SyN control, pair receipts, case aggregation and full denominators.

Temporal aggregation must consume registered logits/features/uncertainty, velocity, integrated displacement, Jacobian, motion magnitude, texture residual, frame quality, temporal position and valid-frame mask. Frame0-only, unregistered primary output, missing-field consumption, cumulative reset/gap/overlap/duplicate, or partial-attempt credit fails closed.

## 5. Fixed training and evaluation budgets

| Stage | Steps | Minimum train-loop seconds | Validation events | Full-case events / cases | Role |
|---|---:|---:|---:|---|---|
| B1 anatomy repair | 2,000 | 600 | 4 | 2 train-only cases | implementation/label gate |
| B3 representation | 6,000 | 1,800 | 3 | 44-case manifest | readiness; B4 follows |
| B4 proposal | 8,000 | 2,400 | 4 | 44-case manifest | OOF/proposal evidence; B5 follows |
| B5 refiner | 10,000 | 3,000 | 5 | 44-case manifest | refiner evidence; B6 follows |
| B6 joint | 8,000 | 2,400 | 4 | four full-case events, 44 cases | first MyoPS full-route judgment |
| B7 pretrained | 8,000 | 3,600 | 4 | four events, 12 cases | official source |
| B7 random | 8,000 | 3,600 | 4 | four events, 12 cases | matched control |
| B8 registration | 25,000 | 7,200 | 10 | four events, 12 cases, at least 60 pairs | SVF/SyN fidelity |
| B9 temporal | 20,000 cumulative | 7,200 | 10 | four events, 12 cases | Cine terminal evidence |

Every selected checkpoint is clean-reloaded. Failed startup, timeout, preemption, incomplete chunk, race loss and partial checkpoint receive zero training credit.

## 6. Same-split and challenge-facing evidence

B0 freezes the exact same-split nnU-Net baseline. B6 reports per-case baseline/model Dice, HD95, remote-FP, component count, volume ratio, lesion-wise recall, changed logits/voxels/components, and help/harm/severe-harm. Required subgroup summaries are scar-positive, T2-present edema-positive, no-T2 safety, CenterB, CenterC, complete tri-modal, remote-FP-positive and high-component-burden.

B9 reports reference-only, unregistered multi-frame, registered temporal, temporal-router-off, motion/Jacobian-off, anatomy-off, uncertainty/quality-off, matched-random, learned-SVF and real-SyN controls on the same cases, frames, downstream checkpoint and decode rule.

Local proxy metrics are not hosted metrics. No validation package or upload is authorized.

## 7. Controller terminal finalizer repair

B10 is now a controller-level terminal finalizer, not a successful-wave executor dependent on B6 and B9 merge receipts.

Machine source: `terminal_finalizer_contract` in `prompts/routes/route_B_round04_executor_plan.yaml`.

The controller writes:

```text
results/route_B/round04/controller_terminal_registry.json
results/route_B/round04/controller_ledger.csv
```

B10 has `depends_on: []`, `prepare_wave_helper_exempt: true`, `depends_on_successful_merge_receipts: false`, and is launched by the controller through an atomic launch lock. Its `afterany` dependency is computed from every started attempt ID in the controller ledger. When no job started, it uses the local deterministic finalizer path.

Launch barrier:

- B0/B1/B2 global terminal blocker or revision: launch B10 immediately.
- After B2: launch only after both MyoPS and Cine lanes have a declared terminal class.
- A B7 blocker or B8 faithful registration blocker terminates the Cine lane while MyoPS continues.
- A B3/B4/B5 implementation revision terminates the MyoPS lane while Cine continues.
- Successful B6 and B9 are also terminal classes.
- Timeout, preemption, failed startup, started/cancelled race loser and success are all retained in accounting.

The B10 static known-bad matrix must exercise B1 failure, B2 external blocker, B7 blocker, B8 registration blocker without B9, timeout, preemption, cancelled race loser and successful B6/B9.

## 8. Exact stage validators and known-bad bindings

Every executor entry now contains a machine-readable `validator` and `known_bad_contract`. The validator command fixes the script, strict mode, input directory, report file, expected exit `0` and success token. The known-bad runner fixes the matrix path, command, report, runner exit `0`, validator exit `1` for every fixture and the exact expected failure keys.

| Stage | Strict validator | Input | Report | Success token | Required known-bad failure keys |
|---|---|---|---|---|---|
| B0 | `scripts/validation/route_B_round04/validate_B0_binding_manifests.py` | `results/route_B/round04/executors/B0` | `results/route_B/round04/executors/B0/validator_report.json` | `ROUTE_B_ROUND04_B0_READY_FOR_CONTROLLER_MERGE` | `STALE_PLANNING_BINDING`, `ROUTE_EVIDENCE_REF_MISMATCH`, `MANIFEST_HASH_MISMATCH`, `ANATOMY_TARGET_LABEL_ROUNDTRIP_FAILED`, `SAME_SPLIT_BASELINE_MISSING`, `VALIDATOR_MATRIX_INCOMPLETE` |
| B1 | `scripts/validation/route_B_round04/validate_B1_anatomy_repair.py` | `results/route_B/round04/executors/B1` | `results/route_B/round04/executors/B1/validator_report.json` | `ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED` | `PURE_MYOCARDIUM_UNION_TARGET`, `ANATOMY_MICRO_OVERFIT_INADEQUATE`, `ROUTED_ANATOMY_GRADIENT_MISSING`, `LATERAL_ANATOMY_GRADIENT_MISSING`, `ANCHOR_SUPPORT_FLOOR_BECAME_FINAL_BASE`, `SAVE_RELOAD_MISMATCH` |
| B2 | `scripts/validation/route_B_round04/validate_B2_implementation_freeze.py` | `results/route_B/round04/executors/B2` | `results/route_B/round04/executors/B2/validator_report.json` | `ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED` | `NNUNET_ONLY_BYPASS`, `DISCONNECTED_RETRIEVAL_PROPOSAL_REFINER`, `INVALID_SLOT_WEIGHT_NONZERO`, `PATTERN_SIP_ALIAS_OR_NO_GRADIENT`, `FAKE_CINEMA_SOURCE_OR_WRONG_SHA`, `DIRECT_VELOCITY_AS_DISPLACEMENT`, `TEMPORAL_REQUIRED_INPUT_UNCONSUMED`, `OFFICIAL_LABEL_ROUNDTRIP_FAILED`, `LEGACY_ROUND03_WRAPPER_BYPASS` |
| B3 | `scripts/validation/route_B_round04/validate_B3_representation.py` | `results/route_B/round04/executors/B3` | `results/route_B/round04/executors/B3/validator_report.json` | `ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL` | `ROUND03_B3_GLOBAL_STOP_REUSED`, `SAMPLER_CONTRACT_MISMATCH`, `FORMAL_TRAINING_INADEQUATE`, `INVALID_SLOT_WEIGHT_NONZERO`, `NO_T2_EDEMA_NONZERO`, `ROUTER_FAMILY_GRADIENT_MISSING`, `LEARNED_ANATOMY_NONFINITE_OR_CONSTANT`, `B3_FULL_ROUTE_NEGATIVE_TOKEN_FORBIDDEN` |
| B7 | `scripts/validation/route_B_round04/validate_B7_cinema_control.py` | `results/route_B/round04/executors/B7` | `results/route_B/round04/executors/B7/validator_report.json` | `ROUTE_B_ROUND04_B7_CINEMA_MATCHED_CONTROL_COMPLETE` | `FAKE_CINEMA_SOURCE_OR_WRONG_SHA`, `CINEMA_LICENSE_OR_COMMIT_MISSING`, `PRETRAINED_RANDOM_ARCHITECTURE_MISMATCH`, `DOWNSTREAM_INITIALIZATION_MISMATCH`, `CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH`, `SOURCE_INITIALIZATION_NOT_ONLY_DIFFERENCE`, `SELECTED_CHECKPOINT_NOT_RELOADED`, `INTERNAL_SMALL_WRAPPER_USED_AS_OFFICIAL` |
| B4 | `scripts/validation/route_B_round04/validate_B4_proposal.py` | `results/route_B/round04/executors/B4` | `results/route_B/round04/executors/B4/validator_report.json` | `ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE` | `OOF_CURRENT_CASE_LEAKAGE`, `OOF_VALIDATION_OR_TEST_LEAKAGE`, `BOOTSTRAP_OR_EMA_FORMAL_BANK`, `NO_T2_EDEMA_NEGATIVE`, `PROTOTYPE_SIMILARITY_DISCONNECTED`, `CONSTANT_PROPOSAL`, `HARD_ROI_DELETION`, `WEAK_VALID_PROPOSAL_PREMATURE_STOP` |
| B8 | `scripts/validation/route_B_round04/validate_B8_registration.py` | `results/route_B/round04/executors/B8` | `results/route_B/round04/executors/B8/validator_report.json` | `ROUTE_B_ROUND04_B8_REGISTRATION_STAGE_COMPLETE` | `DIRECT_VELOCITY_AS_DISPLACEMENT`, `SCALING_SQUARING_STEPS_NOT_SEVEN`, `PROXY_JACOBIAN`, `INVERSE_CONSISTENCY_MISSING`, `SYN_OUTPUT_COPIED_OR_PROXY`, `PAIR_AS_CASE_AGGREGATION`, `FULL_DENOMINATOR_MISSING`, `SELECTED_REGISTRATION_NOT_RELOADED`, `REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME` |
| B5 | `scripts/validation/route_B_round04/validate_B5_refiner.py` | `results/route_B/round04/executors/B5` | `results/route_B/round04/executors/B5/validator_report.json` | `ROUTE_B_ROUND04_B5_REFINER_STAGE_COMPLETE` | `SHARED_UNDIFFERENTIATED_REFINER`, `REFINER_FINAL_EFFECT_ZERO`, `PROPOSAL_TO_FINAL_RETENTION_FAILED`, `SCAR_REMOTE_FP_REGRESSION`, `NO_T2_EDEMA_NONZERO`, `HARD_ROI_DELETION`, `WEAK_B4_CONTROL_MISSING`, `WEAK_FAITHFUL_REFINER_PREMATURE_STOP` |
| B9 | `scripts/validation/route_B_round04/validate_B9_temporal.py` | `results/route_B/round04/executors/B9` | `results/route_B/round04/executors/B9/validator_report.json` | `ROUTE_B_ROUND04_B9_TEMPORAL_TERMINAL_EVIDENCE_READY` | `FRAME0_ONLY_FALLBACK`, `UNREGISTERED_PRIMARY_OUTPUT`, `REQUIRED_TEMPORAL_INPUT_UNCONSUMED`, `CUMULATIVE_RESET_GAP_OVERLAP_DUPLICATE`, `PARENT_HASH_MISSING`, `TIMEOUT_OR_PARTIAL_CREDITED`, `TEMPORAL_FINAL_OUTPUT_EFFECT_ZERO`, `FULL_CINE_ABLATION_MISSING`, `SELECTED_CHECKPOINT_NOT_RELOADED` |
| B6 | `scripts/validation/route_B_round04/validate_B6_myops_terminal.py` | `results/route_B/round04/executors/B6` | `results/route_B/round04/executors/B6/validator_report.json` | `ROUTE_B_ROUND04_B6_MYOPS_TERMINAL_EVIDENCE_READY` | `SAME_SPLIT_BASELINE_MISSING`, `FRESH_FORCE_EVALUATION_MISSING`, `SCAR_POSITIVE_ROWS_MISSING`, `T2_PRESENT_EDEMA_POSITIVE_ROWS_MISSING`, `NO_T2_SAFETY_ROWS_MISSING`, `CENTERB_OR_CENTERC_ROWS_MISSING`, `EMPTY_GT_COUNTED_AS_HELP`, `SUMMARY_MISNAMED_AS_ABLATION`, `SELECTED_CHECKPOINT_NOT_RELOADED`, `FINAL_OUTPUT_INTERVENTION_ZERO_OR_MISSING`, `PROXY_METRIC_AS_HOSTED` |
| B10 | `scripts/validation/route_B_round04/validate_B10_terminal_packet.py` | `results/route_B/round04/executors/B10` | `results/route_B/round04/executors/B10/validator_report.json` | `ROUTE_B_ROUND04_TERMINAL_PACKET_READY_FOR_REVIEW` | `EARLY_TERMINAL_BRANCH_UNREACHABLE`, `B1_FAILURE_FINALIZER_NOT_LAUNCHED`, `B2_EXTERNAL_BLOCKER_FINALIZER_NOT_LAUNCHED`, `B7_BLOCKER_FINALIZER_NOT_LAUNCHED`, `B8_REGISTRATION_BLOCKER_FINALIZER_NOT_LAUNCHED`, `TIMEOUT_PREEMPTION_CANCELLED_LOSER_NOT_ACCOUNTED`, `SUCCESSFUL_B6_B9_NOT_ACCOUNTED`, `PENDING_OR_RUNNING_PRESENTED_AS_COMPLETE`, `AGGREGATION_MISSING_OR_NONZERO`, `SUPERSEDED_RECEIPT_NOT_RECONCILED`, `CONTROLLER_PUSH_OR_REVIEW_AUTHORITY_VIOLATION`, `HEAVY_ARTIFACT_TRACKED`, `VALIDATOR_FILE_EXISTENCE_ONLY` |

A missing key, unexpected fixture pass, file-existence-only validator, mismatched report path, or a validator selected by the controller is a planning/runtime failure.

## 9. Slurm and continuity hardening retained

- `htzhulab` is the default.
- Materially long compatible waits use an isolated `htzhulab+a100-gpu` race.
- Attempts share scientific hashes but never output/log/checkpoint/cache roots.
- One atomic winner lock determines credit; pending losers are cancelled; every loser is zero-credit and accounted.
- `volta-gpu` is credited only for an unchanged scientific configuration whose measured peak memory is at most `14.5 GiB`; semantic downscaling is forbidden.
- Formal wrappers and validator commands use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python`; formal bare `python` is forbidden.
- Training dependencies use `afterok`; B10 finalization uses `afterany` over all started attempts.
- Pending, submitted, running, awaiting-accounting, monitor and undertrained states are not completion.
- The controller must run as a Codex goal/goal resume and remains responsible through terminal accounting, aggregation, mapper final, packet validation, local lightweight commit and reviewer handoff.
- Runtime roles do not push and do not write `review.md`.

## 10. Coordinator receipt and next critic

This Planner does not claim local executable validation. After the final main commit is published, the Codex coordinator must use the receipt template at `prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md` and run the exact commands in `/users/a/e/aereinh/CARE`.

The next Route B critic must stop unless all of the following are true:

1. the receipt status is `READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW`;
2. every required command has exit `0`;
3. the tested commit equals current `origin/main`;
4. the six planning blobs equal the handoff binding;
5. the working tree is clean;
6. no later planning edit made the handoff stale.

Only `ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER` written by the new independent critic permits a later controller start. Planner publication, coordinator validation and Route C evidence completion do not authorize the controller.

## 11. Authority boundary

The following remain false:

```text
controller_authorized_now: 0
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
```
