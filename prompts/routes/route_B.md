---
route_id: route_B
portfolio_round: round02
task_key: route_B_round02_full_srr_v3_cinema_metric_repair
route_name: "Route B — full SRR-v3 with real CineMA evidence and metric-facing retraining"
branch: route_B
worktree: /users/a/e/aereinh/CARE_worktrees/route_B
status: DRAFT_FOR_ROUND02_CRITIC_REVIEW
not_a_milestone: true
planner_main_base_commit: 3f0e78706653da2eeeb3453ed992628a7c0eee70
prior_controller_packet_commit: 0200e86f7a95ff9753f9c425419052e878d342f4
prior_reviewer_commit: cde0e0b658893b327aa5fb3129d37a99f1cf7c47
prior_review_decision: ROUTE_B_REVIEW_NEEDS_REVISION
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
critic_request_path: prompts/routes/route_B_critic_request.md
planner_audit_path: prompts/routes/route_B_planner_audit.md
current_round_critic_required: true
current_round_critic_token: ""
controller_start_authorized: false
route_promotion_authorized: false
validation_upload_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
---

# Route B Round02 controller contract

## 1. Round02 decision and prior evidence

The prior Route B implementation and bounded train/eval are credible: the winning Slurm job completed, `25000` optimizer steps and `1908.338` train-loop seconds were recorded, and real MyoPS/Cine forward, gradients, intervention, save/reload, and export QA were present. The packet is not reviewer-accepted because the packet validator and known-bad tests do not cover the full semantic contract, `validator_implementation_report.json` retained a stale undertrained token, and the evaluated ten MyoPS cases contained no positive edema ground truth. The Cine branch used a real classical transform and real multiframe output effects, but it did not bind real CineMA weights, logits, intermediate features, or uncertainty.

Round02 keeps Route B as the complete SRR-v3 route. The changed training semantics are: exact full SRR-v3 structure, T2-positive-balanced metric-facing evaluation, and a real CineMA feature/logit/uncertainty source with a matched random-initialization representation control. These changes justify one new bounded MyoPS run and two matched Cine runs. Blind repetition of the prior run is forbidden.

## 2. Diagram-derived route objective

Route B must implement the full causal chain:

`modality stems -> availability/spatial router -> shared/private/interaction dictionary -> train/OOF prototype memory -> anatomy decoder -> scar/edema proposals -> pathology-specific soft ROI -> scar/edema refiners -> bounded residual correction -> final output`.

Cine must implement:

`real CineMA multiclass logits/features/uncertainty -> ED/key-frame registration -> registered evidence -> temporal dictionary -> temporal refiner -> final myocardium output`.

nnU-Net is baseline, context, teacher, and bounded safety anchor. It cannot replace retrieval, proposals, refiners, or temporal evidence.

## 3. Exact MyoPS architecture

1. Input and availability order: `[LGE, T2, C0]`.
2. Three modality stems and four encoder scales with channels `[32,64,128,256]`.
3. At each scale, exactly sixteen residual experts: four shared, two LGE-private, two T2-private, two C0-private, and two for each pairwise interaction `(LGE,T2)`, `(LGE,C0)`, `(T2,C0)`.
4. Separate anatomy, scar, and edema two-pass spatial routers. Pass one uses local modality features, availability, anatomy distance, anchor uncertainty, and component/remote-FP flags. Pass two additionally consumes proposal logits. The gate is entmax-1.5; the first 20% of training is soft, the next 30% keeps top four, and the final 50% keeps top two. Invalid slots must have max absolute weight no greater than `1e-8` per batch/task/slot.
5. Pattern-SIP is a real loss over availability group, style cluster, and hard subgroup usage. Target expert mass is `0.50` shared, `0.35` private, and `0.15` interaction. It has an independent tensor, function, and gradient test and is not an alias of dictionary loss.
6. Four deterministic train-only OOF shards. Each pathology has eight positive and twelve negative prototype slots. Memory uses EMA plus a bounded trainable residual and a FIFO provenance ledger. Edema negatives are drawn only from T2-present safe regions; no-T2 myocardium never enters edema positive or negative memory.
7. Anatomy decoder outputs background, myocardium-union, LV, and RV. Scar proposal is LGE-dominant with remote-FP negative memory. Edema proposal is T2-conditioned. Scar soft ROI has two-voxel dilation; edema soft ROI has five-voxel dilation. The refiners are separate modules.
8. With anchor logits `z_anchor`, full SRR logits `z_srr`, and pathology-specific bounded deltas, the final output is:

   `z_final = z_anchor + g_scar*4*tanh(delta_scar) + g_edema*4*tanh(delta_edema)`.

   The correction is zero outside the corresponding soft ROI. The gate consumes route confidence, anchor entropy, anatomy support, component flags, and availability. The implementation must expose on/off interventions for retrieval, memory, proposal, each refiner, gate, and final correction.
9. No-T2 behavior is four-way blocked: no edema supervised loss, no edema memory update, zero edema proposal/refiner correction, and final Route B edema delta exactly zero.

## 4. Exact CineMA and temporal architecture

Route B does not fine-tune the CineMA backbone in Round02. This is a deliberate fixed-source experiment, not a future-work deferral. The complete Cine branch must consume real CineMA evidence now.

CineMA provenance:

- code commit `c10daa1d93f0ea28d8b9ad9206b0f673d25805c1`;
- Hugging Face revision `b1251ee50423bceeca84c080782fc3bc7756dea6`;
- MIT license;
- source `https://huggingface.co/mathpluscode/CineMA/resolve/main/finetuned/segmentation/acdc_sax/acdc_sax_0.safetensors`;
- SHA256 `c7a60195e6c0aa920b0d0d8221d2ea7a75b6a5ea570763c3bf4924398f5ae85f`;
- route-local untracked path `/users/a/e/aereinh/CARE_worktrees/route_B/results/route_B/runtime/external_assets/CineMA/acdc_sax/acdc_sax_0.safetensors`.

The source emits four-class anatomy logits, a sixteen-channel last-decoder feature map, and normalized entropy. The pretrained source is frozen. A matched control instantiates the same `ConvUNetR` architecture from deterministic random seed `26071722`, also frozen. Both feed identically initialized/trainable `1x1` feature projections, registration inputs, eight-slot temporal dictionaries, and temporal refiners. Trainable parameter counts must match exactly.

Frames are ED/frame `0` plus eight evenly spaced non-reference frames across the first `4/6` of the cardiac cycle. Registration is ANTsPy `SyNOnly` to ED. Each case requires at least four passed non-reference frames. The temporal dictionary has exactly eight slots: ED anatomy anchor, early/late systolic contraction, early/late diastolic relaxation, motion magnitude, registered texture residual, and registration-uncertainty safety.

The temporal head consumes registered CineMA features and logits, ED features/logits, transform displacement, Jacobian determinant, intensity residual, and uncertainty. It uses a thirty-two-channel projection, masked slot retrieval, two residual convolution blocks, and a four-class output. It must alter final logits and labels on real cases. Binary priors, frame0 fallback, union-only aggregation, descriptor-only retrieval, and topology-only completion are forbidden.

The matched pretrained/random runs use the same cases, frames, preprocessing, augmentation, optimizer, number of trainable parameters, budget, validation cadence, checkpoint schedule, and selection rule. The only difference is CineMA source initialization. The pretrained benefit classification is evidence, not an assumption.

## 5. Fixed data, baseline, and split contracts

Shared read-only root: `/users/a/e/aereinh/CARE`.

MyoPS primary evaluation is the exact prior 44-case fold-0 case list, frozen by SHA256. The T2-positive edema manifest is every fold-0 case with T2 present and positive edema ground truth, sorted by case ID. It must contain at least eight cases. Training uses deterministic pathology-balanced sampling: half of batches are drawn from T2-present edema-positive cases, one quarter from scar-positive cases, and one quarter from the remaining cases. This sampling changes training semantics and must be included in the fingerprint.

Cine uses twelve labeled training cases, six per center after sorted case-ID selection, with 4D image and reference label paths under the shared data root. The same twelve cases and frames are used for pretrained and random controls.

The immutable nnU-Net baseline root is:
`/users/a/e/aereinh/CARE/results/submissions/care_myocardium_validation/workspaces/nnUNet_MyoPS+nnUNet_CineMyoPS_5fold_baseline_round8_20260519_084057/predictions`.

## 6. Ordered controller task graph

1. `B0_BIND_AND_REVIEW_REPAIR`: bind current main policies, exact route task/plan hashes, prior packet/evidence hashes, data/split/baseline manifests, and external asset provenance.
2. `B1_STRICT_VALIDATOR_REPAIR`: expand packet validator, implementation validator, and executable known-bad fixtures; remove the stale undertrained token only when current evidence supports the replacement state.
3. `B2_FULL_ARCHITECTURE_RECONCILIATION`: map current implementation against the exact sixteen-slot/OOF/Pattern-SIP/proposal/refiner/bounded-correction contract; implement missing pieces and the real CineMA source/control path.
4. `B3_IMPLEMENTATION_GATE`: real LGE-only, LGE+C0, complete-trimodal, and no-T2 forward/gradient/intervention tests; real CineMA load; real pretrained/random feature difference; real SyN; temporal input consumption; save/reload/export; no old-wrapper bypass.
5. `B4_MYOPS_FULL_BOUNDED_TRAIN_EVAL`: one full-architecture bounded run with the new pathology-balanced sampling and frozen 44-case/T2-positive evaluation.
6. `B5_CINE_PRETRAINED_MATCHED_RUN`: one frozen-pretrained CineMA temporal run.
7. `B6_CINE_RANDOM_MATCHED_RUN`: one frozen-random CineMA temporal run with exactly the same contract as B5.
8. `B7_SELECTED_CHECKPOINT_RELOAD_AND_INTERVENTIONS`: enumerate all scheduled checkpoints from B4/B5/B6, apply the exact selection rules, clean-reload the selected checkpoints, and perform final-output interventions.
9. `B8_FINALIZER_A`: `afterany` accounting and aggregation over every attempt.
10. `B9_MAPPER_FINAL_AND_FINALIZER_B`: route-local architecture/fingerprint finalization, strict validators, known-bad self-tests, `git diff --check`, one local lightweight commit, and controller stop.
11. `B10_INDEPENDENT_REVIEWER_HANDOFF`: create the separate read-only reviewer request.

## 7. Training budgets and optimizers

MyoPS: AdamW, learning rate `1e-4`, weight decay `1e-4`, batch size `1`, gradient clip `5.0`, seed `26071721`. It must reach `25000` optimizer steps and `3600` train-loop seconds, four validation events, all 44 primary cases, at least eight T2-positive edema-positive cases, one-batch overfit, finite/nonzero mechanism losses, loss decrease, prediction sanity, same-split baseline, and cache isolation.

Each Cine control: AdamW on only projection/temporal parameters, learning rate `2e-4`, weight decay `1e-4`, batch size `1` case, gradient clip `5.0`. Pretrained seed is `26071722`; random source initialization seed is also `26071722`, while data-order seed is `26071723` for both. Each reaches `8000` steps and `3600` seconds, four validation events, twelve cases, ED plus eight non-reference frames, one-batch overfit of trainable heads, loss decrease, prediction sanity, same-case frame0 control, and isolated cache/checkpoint roots.

Scheduled checkpoints are steps `2000, 4000, 6000, 8000` for Cine and `5000, 10000, 15000, 20000, 25000` for MyoPS. A selected checkpoint is not privileged until clean reload reproduces logits within `1e-5`.

## 8. Selection rules and metric gates

MyoPS checkpoint eligibility requires: complete case manifests and hashes; no-T2 Route B edema delta exactly zero; nonempty prediction rate at least `0.80` on positive cases; pathology volume ratio in `[0.25,4.0]`; no NaN/Inf; all implementation and packet validators passing.

Eligible checkpoints are ordered lexicographically by: maximize the smaller of scar Dice delta and T2-positive edema Dice delta; minimize positive HD95 deltas; minimize remote-FP delta; minimize component-count delta; select the earlier step on an exact tie.

Cine source/checkpoint ordering is exact:

1. For each source, select the checkpoint with highest mean myocardium Dice; ties within `0.001` use lower mean HD95, then earlier step.
2. Classify `PRETRAINED_BENEFIT` only when pretrained mean Dice exceeds random by at least `0.01` and pretrained HD95 is no worse by more than `1.0 mm`.
3. Classify `RANDOM_NONINFERIOR` when absolute Dice difference is at most `0.005` and random HD95 is no worse.
4. Otherwise classify `CINEMA_CONTROL_UNRESOLVED`; Route B cannot be candidate-ready.
5. Downstream Route B outputs always use the clean-reloaded pretrained checkpoint. Random control never silently replaces CineMA and cannot erase the required pretrained evidence path.

Route-level metric gates:

- scar: Dice delta at least `+0.01` or HD95 delta at most `-1.0 mm`, with remote-FP non-increase and severe-harm fraction no greater than `0.20`;
- edema: T2-positive Dice delta at least `+0.02` or HD95 delta at most `-1.0 mm`, with exact no-T2 zero delta;
- Cine: pretrained temporal Dice delta versus frame0 at least `+0.01`, HD95 no worse by more than `1.0 mm`, and temporal on/off changes labels on at least eight of twelve cases.

A reviewer may accept an adequate negative packet, but candidate-ready requires all safety gates, full mechanism closure, and at least two positive metric gates while the third is non-worse.

## 9. Slurm contract

Formal wrappers use `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python` or an exactly fingerprinted route-local equivalent. No bare `python`.

B4 runs on `htzhulab`. B5 runs after B4 is terminal; B6 runs after B5 is terminal. Default walltime is six hours per job. After two two-hour pending checks, an identical `a100-gpu` mirror may be submitted with isolated output and an atomic winner lock. `volta-gpu` is not used. Training-to-training chains use `afterok` only when the downstream phase requires successful upstream artifacts; the global finalizer uses `afterany` over every attempt. Scheduler block requires 24 hours of all submitted routes remaining pending.

## 10. Write scopes, packet, validators, and reviewer

Allowed writes: `src/care_myocardium/route_B/**`, the exact full SRR-v3 first-party files named in the implementation snapshot, `scripts/route_B/**`, `scripts/training/route_B/**`, `scripts/validation/route_B/**`, `tests/route_B/**`, `configs/route_B/**`, `jobs/route_B/**`, `results/route_B/**`, and `logs/route_B/**`. Any shared first-party file edit must be declared before editing in `implementation_snapshot.md`, remain on `route_B`, and be included in mapper/fingerprint receipts. Route A/C, root current state, submissions, raw data, and shared prompts are forbidden writes.

Required packet files include all Agent-Flow v2 controller receipts plus: `full_architecture_inventory.json`, `invalid_slot_runtime.csv`, `pattern_sip_runtime.csv`, `prototype_memory_provenance.csv`, `mechanism_intervention_matrix.csv`, `cinema_provenance.json`, `cinema_pretrained_random_control.csv`, `cine_registration_temporal_report.csv`, `training_adequacy.csv`, `metrics_summary.csv`, `case_safety_matrix.csv`, `help_harm_matrix.csv`, `same_split_baseline_receipt.json`, `label_cache_audit.json`, route-local mapper/fingerprint files, finalizer state, strict validator reports, commands, result/controller/completion/review request, and manifest.

Strict validators must parse adequacy thresholds, Slurm terminal accounting, aggregation, controller/finalizer consistency, all mechanism outputs, hashes, and authority fields. Known-bad fixtures must fail for config/mock/CSV-only modules, old-wrapper bypass, invalid slot gradients, router input bypass, prototype leakage, no-T2 edema negative, no-effect proposal/refiner/gate, unbounded correction, fake/frame0 CineMA, unmatched random control, temporal not consuming registered evidence, undertrained ready, submitted-only packet, stale token, heavy artifacts, push/review, or forbidden authority.

The durable finalizer performs terminal accounting, aggregation, mapper final, strict validation, and one local lightweight commit. It does not push or write `review.md`. The independent reviewer is read-only and post-commit. Reviewer acceptance authorizes only later portfolio comparison.
