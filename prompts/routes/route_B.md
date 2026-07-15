---
route_id: route_B
route_name: "Route B — full SRR-v3 architecture implementation"
branch: route_B
worktree: /users/a/e/aereinh/CARE_worktrees/route_B
status: CRITIC_REVISED_READY_FOR_CONTROLLER
not_a_milestone: true
planner_base_commit: dfea8e1bb22de1bbcf3ff062359f1dd086f56c38
critic_reviewed_planner_commit: 7303ef937793e47f5bac562e3c2c796654acc7fa
critic_decision: APPROVE_AFTER_REVISION
critic_token: ROUTE_B_PLANNING_READY_FOR_CONTROLLER
diagram_source: "ChatGPT Project background materials / current conversation visual channel"
diagram_versions_read:
  - SRR-v2
  - SRR-v2.5
  - SRR-v3
visual_read_status: READ_FROM_CURRENT_PROJECT_BACKGROUND
canonical_repo_paths:
  - images/SRR-v2.png
  - images/SRR-v2.5.png
  - images/SRR-v3.png
critic_required: true
critic_request_path: prompts/routes/route_B_critic_request.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
allowed_critic_token: ROUTE_B_PLANNING_READY_FOR_CONTROLLER
forbidden_tokens:
  - ROUTE_PROMOTED
  - VALIDATION_UPLOAD_APPROVED
  - HOSTED_METRIC_CLAIM
  - M11_AUTHORIZED
  - FINAL_SCIENTIFIC_CONCLUSION
  - CROSS_ROUTE_MERGE_APPROVED
---

# Route B planning contract

Route B is not a milestone. It is the isolated medium-work route for turning the complete SRR-v3 MyoPS and Cine design into executable, auditable code before formal training. The route cannot pass by creating interfaces, configs, tables, wrappers, mocks, or conceptual modules that do not causally affect final outputs.

## Independently recovered SRR-v3 objective

The v2 diagram establishes availability-aware selective retrieval from LGE, C0/bSSFP and T2, followed by anatomy-guided lesion proposal and pathology-specific soft-ROI refinement. v2.5 makes scar and edema proposal paths explicitly separate: scar is LGE-dominant and high precision; edema is T2-conditioned and broader context. v3 adds a semantic multi-slot representation bank with real train/OOF prototype groups, nnU-Net probabilities/logits, components, uncertainty and anatomy context, and a baseline-preserving bounded residual correction. Cine remains a registration-aware anatomy-first temporal path: ED/reference and selected key frames are warped into a reference space, routed through a temporal representation dictionary, and aggregated with frame-wise anatomy evidence. It is not a single-frame or topology-only side path.

The required causal chain is:

```text
observed modalities + availability
-> modality-specific stems and multi-scale encoder
-> availability-and-image-aware routing
-> shared/private/optional-interaction semantic retrieval
-> anatomy + scar/edema proposals
-> pathology-specific soft-ROI refiners
-> bounded nnU-Net-anchored residual correction
-> official-label output
```

## Route objective and implementation-first hard gate

The first success criterion is implementation fidelity, not leaderboard score:

```text
code completion
-> real-case forward
-> finite nonzero losses
-> gradients to every required trainable module
-> controlled interventions change final logits/labels
-> checkpoint save/reload/resume consistency
-> official-label/export QA
-> implementation freeze
-> only then formal training/evaluation
```

Formal training is forbidden until the complete MyoPS and Cine implementation gate passes. A Cine blocker may be reported honestly, but it is a failing implementation state and cannot be used to let MyoPS training bypass the complete Route B gate.

## Portfolio position and isolation

Route B implements the complete architecture. It is larger than Route A, which is the quickest compressed non-pure-nnU-Net candidate, and smaller in evidence-reconciliation scope than Route C, which inherits M10 follow-up2 replay and Cine fidelity accounting. Route B must not absorb Route C's historical-evidence burden or degrade to Route A's compressed architecture.

| item | value |
| --- | --- |
| branch | `route_B` |
| worktree | `/users/a/e/aereinh/CARE_worktrees/route_B` |
| controller tmux | `care_route_B_controller` |
| reviewer tmux | `care_route_B_reviewer`, created only after packet commit |
| result root | `results/route_B/` |
| runtime root | `results/route_B/runtime/` |
| log root | `logs/route_B/` |
| lock root | `results/route_B/locks/` |

Allowed branch-local source and lightweight-evidence writes:

- `src/care_myocardium/srr_v3/**`
- `src/care_myocardium/route_B/**`
- `scripts/route_B/**`
- `scripts/diagnostics/route_B/**`
- `scripts/training/route_B/**`
- `scripts/validation/route_B/**`
- `tests/route_B/**`
- `configs/route_B/**`
- `jobs/route_B/**`
- `results/route_B/**`
- `logs/route_B/**`

Runtime-only checkpoints, prediction volumes, transform fields and caches may be written only below `results/route_B/runtime/**`. They must remain untracked and must never enter the lightweight packet or Git commit. This runtime allowance is necessary for real save/reload/export testing and formal train/eval; it does not authorize publication of heavy artifacts.

Forbidden writes and actions:

- `prompts/shared/**` without later portfolio-level authorization;
- Route A/C source, result, runtime, log or lock namespaces;
- root `wiki/current_state.yaml` or `wiki/history/**` before portfolio reconciliation;
- `results/submissions/**`, validation packages or uploads;
- raw data modification, secrets, environment dumps, heavy logs, checkpoints or NIfTI files in Git;
- route promotion, M11, final scientific conclusion or cross-route merge.

Because portfolio policy defers root wiki mutation, the mapper must instead produce route-local architecture receipts and fingerprints under `results/route_B/`. Final root-wiki reconciliation remains a later portfolio action.

## MyoPS architecture contract

All required modules must be real code paths:

1. LGE, C0/bSSFP and T2 modality-specific stems;
2. multi-scale encoder;
3. router reading both availability and pooled image-derived features;
4. shared dictionary at every declared scale;
5. LGE-private, C0-private and T2-private dictionaries;
6. optional interaction dictionary with tested on/off intervention;
7. real train/OOF prototype bank with scar-positive, scar-safe-negative, edema-positive and T2-present edema-safe-negative groups;
8. anatomy decoder producing union, LV, RV and anatomy-context evidence;
9. LGE-dominant scar proposal decoder;
10. T2-conditioned, broader-context edema proposal decoder;
11. soft-ROI generator using proposal, anatomy, distance, uncertainty and nnU-Net context;
12. small-ROI high-resolution scar refiner;
13. large-ROI context-preserving edema refiner;
14. pathology-specific bounded residual correction around the nnU-Net anchor;
15. final compact-to-raw CARE label/export path;
16. checkpoint save/reload/resume/export support.

Prototype provenance must be case- and fold-safe. A case cannot retrieve a prototype computed from its own ground truth or prediction, and validation/test data cannot update the bank. Edema safe negatives inside myocardium are legal only for T2-present cases with valid edema supervision; no-T2 myocardium cannot become edema negative.

The v3 residual contract is explicit:

```text
z_final = z_nnunet + g_scar * delta_z_scar + g_edema * delta_z_edema
```

`g_scar` and `g_edema` are element-wise gates in `[0,1]`; residual maps are bounded by declared limits. Closed gates must reproduce the nnU-Net anchor within a declared numerical tolerance. Open-gate interventions must change final logits or labels on real cases. The gate must use uncertainty/error-prone context and include a help/harm receipt; a generic unconstrained residual head or identity wrapper is invalid.

The loss family must include anatomy, scar proposal, edema proposal, scar refinement, edema refinement, residual/gate, negative-space/hard-negative, dictionary/prototype, prior/ROI and optional alignment terms. Only diagram-marked optional modules—interaction dictionary and alignment—may be disabled without changing Route B's identity. Any required term cannot be silently disabled by the controller.

## Cine architecture contract

Route B must implement Cine rather than defer it:

1. a real CineMA or approved anatomy-source loader with provenance, license and weight/init receipt;
2. frame-wise multiclass anatomy logits, features and uncertainty;
3. ED/reference determination and deterministic key-frame policy;
4. registration interface producing actual transforms and warped evidence;
5. if learned registration is used, real symmetric velocity, scaling-and-squaring, Jacobian, inverse-consistency and registration losses;
6. a real ANTs/SyN or comparable classical registration control;
7. temporal representation dictionary with frame-quality or motion-saliency routing;
8. temporal aggregation/refiner consuming registered anatomy, features, motion and uncertainty;
9. checkpoint/resume/export/layout QA.

The implementation gate must use at least three real cine cases and at least three non-reference frames per case. Temporal on/off intervention must alter final output on the tested cases. Frame0-only, descriptor-only, topology/LCC-only, optical-flow-only proxy, untrained VoxelMorph, mock transforms, or an “honest blocker” labeled as pass are invalid. A genuine blocker is reported as `ROUTE_B_IMPLEMENTATION_NEEDS_REVISION` or `ROUTE_B_NEEDS_EVIDENCE` and blocks formal training.

## Implementation-before-training checks

### MyoPS

- Real forward for LGE-only, LGE+C0 and LGE+C0+T2.
- Perturbing the tensor for an unavailable modality while keeping its availability bit off leaves outputs invariant within tolerance and produces no gradient through that unavailable input.
- Changing availability or an actually observed modality changes routing/output where expected.
- Every required module appears in an architecture trace with code path, tensor shape, parameter count, provenance and final-output dependency.
- Losses are finite, nonconstant and nonzero where expected; gradients reach stems, router, dictionaries/prototypes, anatomy, proposals, refiners and gates.
- No-T2 edema proposal/refinement losses are exactly masked according to contract.
- Major-module on/off interventions alter final logits/labels.
- Closed residual gates reproduce the anchor; open gates produce bounded changes and record help/harm.
- Save/reload and resume preserve output/state within tolerance.
- Export maps compact labels to official CARE values and records voxel/hash checks.

### Cine

- Real multi-frame input and frame ordering are consumed.
- Real anatomy logits/features/uncertainty are loaded or computed.
- Registration produces traceable warp statistics and transformed evidence.
- Temporal dictionary/refiner consumes registered evidence rather than filenames or descriptors.
- Temporal enabled/disabled and registered/unregistered interventions alter final outputs on the required multi-case set.
- Resume does not reset temporal state.
- Export maps to the official layout.

### Freeze

After all checks pass, record code/config/data-split/case-list/label/preprocess/decode/export hashes. Any architecture, loss or routing semantic change invalidates the freeze and requires the full gate to rerun.

## First bounded train/eval after freeze

The first formal wave is limited to eight hours per job. Minimum effective training evidence is machine-readable and requires at least:

- `min_optimizer_steps: 500`;
- `min_train_loop_seconds: 1800`;
- `min_validation_events: 2`;
- `min_eval_cases: 10` for MyoPS and `min_cine_eval_cases: 5` for Cine;
- one-batch overfit, prediction sanity, loss decrease, cache isolation and same-split nnU-Net/Cine baseline checks.

Falling below these thresholds is smoke or undertrained evidence. It may support debugging but cannot support portfolio acceptance, route promotion or scientific stop. Reports must include modality groups, T2-present/GT-positive edema, no-T2 safety, CenterB/CenterC where available, scar-positive cases, remote false positives, components, HD95 and volume-ratio guardrails.

## Slurm routing

Use `htzhulab` first, `a100-gpu` second and `volta-gpu` third. V100 use requires an explicit 16-GB compatibility receipt without scientific-semantic changes. Prefer distinct ready work on different partitions. A duplicate race is allowed only for one critical pending logical run with identical hashes/semantics, isolated attempts, one atomic winner lock, loser receipts and pending-loser cancellation.

Pending, running, watcher, monitor or `AWAITING_SACCT` states are not completion. Final aggregation must occur after terminal accounting and must merge runtime evidence into tracked lightweight files.

## Required validators and known-bad fixtures

The controller must implement and run:

- `scripts/validation/route_B/validate_route_b_implementation.py`;
- `scripts/validation/route_B/validate_route_b_packet.py`;
- `tests/route_B/known_bad/` fixtures covering semantic bypasses;
- the repository executor-plan, controller-packet and route-isolation validators applicable to this task.

Strict mode is mandatory. The validators must fail at least these cases:

- placeholder/mock/dataclass/config/CSV-only module;
- old nnU-Net or Cine wrapper bypass;
- unavailable-modality perturbation affects output while availability is off;
- router ignores pooled image features or availability;
- prototype has self-case, fold or validation leakage;
- no-T2 edema negative supervision;
- proposal/refiner/gate has no final-output effect;
- residual closed gate is not anchor identity or residual is unbounded;
- Cine frame0/descriptor/topology/proxy-registration path;
- temporal module does not consume registered tensors;
- formal training predates freeze receipt;
- known pending/monitor packets claim completion;
- missing controller lifecycle receipts;
- heavy runtime artifacts are staged for Git;
- upload, promotion, M11 or cross-route merge claim.

## Result packet and controller lifecycle

The lightweight packet under `results/route_B/` must contain:

- `controller_context.json`, `controller_ledger.csv`, `controller_bootstrap_snapshot.md`;
- `implementation_gap_inventory.md`, `implementation_snapshot.md`;
- `architecture_component_trace.csv`, `architecture_delta_final.md`;
- `mapper_report_draft.md`, `mapper_report_final.md`;
- `implementation_gate.md`, `implementation_gate.json`;
- `gradient_and_intervention_report.csv`;
- `save_reload_export_report.json`, `implementation_freeze_receipt.json`;
- `cine_registration_temporal_report.csv`;
- `finalizer_state.json`, validator reports;
- `result.md`, `commands_run.md`, `controller_report.md`;
- `completion_check.md`, `review_request.md`, `MANIFEST.md`.

Training/eval files are required only if the post-freeze wave runs: `training_adequacy.csv`, `metrics_summary.csv`, `case_safety_matrix.csv`. Missing formal training must be classified as undertrained/evidence-incomplete, never as scientific completion.

`completion_check.md` must contain exactly one controller completion token from the allowed set. Only `ROUTE_B_READY_FOR_REVIEW` permits the independent reviewer to start; it does not imply scientific acceptance.

## Reviewer contract

The reviewer is a separate read-only session pinned to the committed packet. It must independently rerun strict validators and inspect architecture-to-code/tensor/output mappings, implementation ordering, intervention effects, gradient reachability, anchor identity, save/reload/export, Cine registration/temporal fidelity, training adequacy and monitor-state absence. It must not fix files, train, package, upload, promote, start M11 or merge routes.

The reviewer may issue only:

- `ROUTE_B_REVIEW_PACKET_ACCEPTED_FOR_PORTFOLIO_COMPARISON`;
- `ROUTE_B_REVIEW_NEEDS_EVIDENCE`;
- `ROUTE_B_REVIEW_NEEDS_REVISION`;
- `ROUTE_B_REVIEW_NEEDS_MONITOR`.

## Stop, finalizer and authorization boundary

Stop with `ROUTE_B_IMPLEMENTATION_NEEDS_REVISION` when any required module is missing/no-op, Cine is incomplete, gradients/interventions fail, or save/reload/export is inconsistent. Use `ROUTE_B_SCIENTIFIC_UNDERTRAINED` when implementation is real but training is inadequate. Use `ROUTE_B_NEEDS_EVIDENCE` for missing artifacts and `ROUTE_B_NEEDS_MONITOR` for nonterminal jobs.

The finalizer performs terminal accounting, aggregation, mapper-final handoff, strict validation, `git diff --check`, manifest generation and one local lightweight commit. It must not write runtime `review.md`, push, upload validation, claim hosted metrics, promote the route, start M11 or merge another route.

The token `ROUTE_B_PLANNING_READY_FOR_CONTROLLER` authorizes only a later Route B controller start. It does not authorize validation upload, route promotion, final scientific conclusion, M11, package submission or cross-route merge.
