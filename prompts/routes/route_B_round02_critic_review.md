---
route_id: route_B
portfolio_round: round02
role: critic
status: PLANNING_NEEDS_REVISION
reviewed_branch: route_B
reviewed_commit: 77fbde2e1936d19c9f0d6dc711ea37b4ae077eac
route_head_at_review: 77fbde2e1936d19c9f0d6dc711ea37b4ae077eac
route_head_match: true
handoff_path: prompts/routes/handoffs/route_B_round02_critic_handoff_20260717.md
handoff_blob_sha: ab1d09815d833a6c01fcce2c13766a1604d2e302
contract_path: prompts/routes/route_B.md
expected_contract_blob_sha: 0608f6570d7bbb7aeaa919294abb2210eecbb327
observed_contract_blob_sha: 0608f6570d7bbb7aeaa919294abb2210eecbb327
contract_blob_match: true
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
expected_executor_plan_blob_sha: 49fecee5bd77572392096e94f0c1e823570076d5
observed_executor_plan_blob_sha: 49fecee5bd77572392096e94f0c1e823570076d5
executor_plan_blob_match: true
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
decision_token: ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
hosted_metric_claim_authorized: false
cross_route_merge_authorized: false
final_scientific_decision_authorized: false
prompts_shared_modified: false
---

# Route B Round02 Planning Critic Review

## 1. Scope and binding result

This was a planning-only Critic review. No implementation code was edited, no model was trained, no Slurm job was submitted, no runtime `review.md` was written, and no validation, M11, route-promotion, hosted-metric, cross-route-merge, or final-scientific action was performed.

The current `main` entrypoint identifies `round02` and binds Route B to commit `77fbde2e1936d19c9f0d6dc711ea37b4ae077eac`. Immediately before writing this review, remote `route_B` was identical to that commit. Re-fetching the two handoff-bound files produced the required Git blob identities:

| binding | expected | observed | decision |
| --- | --- | --- | --- |
| Route B head | `77fbde2e1936d19c9f0d6dc711ea37b4ae077eac` | `77fbde2e1936d19c9f0d6dc711ea37b4ae077eac` | match |
| contract blob | `0608f6570d7bbb7aeaa919294abb2210eecbb327` | `0608f6570d7bbb7aeaa919294abb2210eecbb327` | match |
| executor-plan blob | `49fecee5bd77572392096e94f0c1e823570076d5` | `49fecee5bd77572392096e94f0c1e823570076d5` | match |

The handoff was therefore current and eligible for substantive review.

## 2. Required sources read

Main-branch policy and round sources read:

- `prompts/routes/handoffs/CURRENT.md`
- `prompts/routes/handoffs/route_B_round02_critic_handoff_20260717.md`
- `AGENTS.md`
- `START_HERE_FOR_GPT.md`
- `GPT_PLANNER_CARE_PROTOCOL.md`
- `prompts/AGENT_FLOW_V2_PROTOCOL.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`
- `prompts/routes/README.md`
- `prompts/routes/route_portfolio_planner_prompt.md`
- `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`
- `prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md`
- `routes/README.md`
- `wiki/README.md`
- `.agents/skills/slurm-routing-partition/SKILL.md`
- `.agents/skills/care-mapper/SKILL.md`

Exact Route B planning files read at the reviewed commit:

- `prompts/routes/route_B.md`
- `prompts/routes/route_B_executor_plan.yaml`
- `prompts/routes/route_B_critic_request.md`
- `prompts/routes/route_B_planner_audit.md`

Prior Route B packet and reviewer evidence read:

- prior controller packet commit `0200e86f7a95ff9753f9c425419052e878d342f4`
- prior reviewer commit `cde0e0b658893b327aa5fb3129d37a99f1cf7c47`
- `results/route_B/result.md`
- `results/route_B/controller_report.md`
- `results/route_B/completion_check.md`
- `results/route_B/review.md`
- `results/route_B/training_adequacy.csv`
- `results/route_B/metrics_summary.csv`
- `results/route_B/case_safety_matrix.csv`
- `results/route_B/bounded_train_eval_summary.json`
- `results/route_B/implementation_gate.json`
- `results/route_B/architecture_component_trace.csv`
- `results/route_B/gradient_and_intervention_report.csv`
- `results/route_B/save_reload_export_report.json`
- `results/route_B/cine_registration_temporal_report.csv`
- `results/route_B/finalizer_state.json`
- `results/route_B/validator_packet_report.json`
- `scripts/validation/route_B/validate_route_b_packet.py`
- `scripts/validation/route_B/validate_route_b_implementation.py`
- `results/20260714_srr_v3_m10_followup_cine_fidelity/cinema_provenance_contract.json`
- `scripts/training/run_cinema_adapter_m10_followup.py`

## 3. Independent visual interpretation

The SRR diagrams were read visually from the current Project/current-conversation image channel rather than inferred from repository PNG metadata or the Planner summary.

- **SRR-v2** establishes availability-aware modality-specific evidence extraction, a shared/private retrieval bank, anatomy-guided scar and edema proposals, pathology-specific soft-ROI refinement, and a registration-aware Cine temporal branch.
- **SRR-v2.5** makes the scar and edema proposal decoders and their refinement geometries explicitly separate rather than allowing one generic terminal dense head.
- **SRR-v3** adds semantic train/OOF prototype groups, nnU-Net logits/components/uncertainty/anatomy context, and pathology-specific bounded corrections that preserve the anchor when gates are closed. Its Cine path requires ED/key-frame reference-space registration, registered anatomy/features/motion/uncertainty, temporal retrieval, and final-output aggregation.

The reviewed plan's intended sixteen-slot, four-scale, two-pass spatial router is a legitimate exact implementation choice for this full v3 objective. The Critic does not find Route B reduced to Route A, a residual-only head, an nnU-Net wrapper, or validator-only work.

## 4. Prior evidence judgment

The Planner accurately describes the prior packet. The terminal Slurm winner completed and the packet recorded `25000` optimizer steps, `1908.338` train-loop seconds, two validation events, ten MyoPS cases, and five Cine cases. However, every evaluated MyoPS case had zero edema ground-truth voxels, so `myops_edema` was `NaN`; the prior Cine implementation used a classical local proxy rather than a real CineMA representation source. The independent reviewer also found that the packet and implementation validators covered only a small subset of the semantic bypasses required by the contract, and that the implementation validator retained a stale undertrained token.

Round02 materially changes the scientific protocol by adding pathology-balanced sampling, a minimum of eight T2-present edema-positive evaluation cases, the complete sixteen-slot/Pattern-SIP/OOF chain, and real frozen CineMA versus a frozen matched random representation source. A new run is therefore scientifically distinguishable from blind repetition. This part of the plan passes.

## 5. Planning blockers

The scientific direction is appropriate, but the contract is not yet controller-forward under the no-blank-design rule. The following are hard planning blockers.

### 5.1 The ordered task graph lacks exact phase result contracts

`route_B_executor_plan.yaml` lists `B0` through `B10`, dependencies, and blocking flags, but it does not assign each phase an exact `result_dir`, exact required output filenames, exact command/entrypoint, validator command, success token, failure states, or next-state transition. A global packet-file list cannot prove which blocking phase completed or prevent a later phase from substituting a similarly named summary.

Required revision: for every `B0`–`B10` node, bind an exact result directory, required files with schemas, executable command or deterministic action, entry gate, success condition, failure/monitor states, and next permitted node. Missing output from any blocking node must be machine-classified as incomplete.

### 5.2 Data and sampling semantics are not fully frozen

The contract refers to an exact prior 44-case fold-0 list “frozen by SHA256” but does not state the manifest path or the SHA256 value. It defines the T2-positive edema manifest procedurally but gives no exact manifest path, generation command, label source/hash, or pre-training validator report. The twelve Cine cases are described as six per center after sorted selection, but the center identities, exact case IDs, manifest path, and manifest hash are absent.

The pathology-balanced sampler also leaves overlap semantics unresolved: a case may be both T2-present edema-positive and scar-positive, yet the plan does not define disjoint precedence, replacement policy, epoch/step sampling schedule, or the exact sampler receipt. The controller would therefore decide scientific training semantics.

Required revision: bind exact MyoPS/Cine manifest paths and hashes; define the command that generates and validates the positive-edema manifest before any training; fail before B4 when fewer than eight qualifying cases exist; list or hash-bind the twelve Cine cases and centers; and define disjoint sampler strata, overlap precedence, replacement policy, seed, per-step proportions, and runtime count receipt.

### 5.3 Pattern-SIP and the full loss are structurally named but not numerically specified

The plan fixes target mass `0.50/0.35/0.15`, but it does not define the Pattern-SIP equation, style-cluster construction/count/update rule, hard-subgroup encoding, coefficient, warm-up behavior, or how the objective combines with anatomy, proposal, refiner, memory, residual, ROI, and final losses. Likewise, “residual expert” does not identify the exact block topology or source symbols to be used at all four scales.

Required revision: specify the exact Pattern-SIP tensor formula and reduction, all group/style definitions, every loss coefficient and activation schedule, the four-scale expert block topology, and the exact first-party source/config symbols. These details must be mirrored in the executor plan and validator schema rather than chosen during B2.

### 5.4 Shared-source write scope remains controller-selected

The executor plan permits edits to an unspecified shared first-party file when an inventory later “proves” that a required symbol lives there; the exact file and symbol are then to be named in `implementation_snapshot.md`. This makes write authorization depend on a controller-created receipt rather than the reviewed plan.

Required revision: enumerate the exact shared first-party paths and symbols that may be edited, or prohibit shared-source edits and require route-local adapters. Any newly discovered shared path must force a new planning revision, not expand scope during execution.

### 5.5 The CineMA adapter and registration interface are not executable without design choices

The weight URL, license, revisions, and SHA are well specified. The existing cited CineMA evidence, however, is explicitly contract-only and reports `case_frame_count: 1`; its entrypoint exits outside `--print-contract`. Round02 does not name the exact real loader/adapter source file and symbol, the external feature hook, the 2D-slice-to-3D/4D assembly rule, orientation/spacing resampling, normalization, interpolation, uncertainty formula, or the feature/logit alignment into the registered temporal path.

`ANTsPy SyNOnly` is named, but exact transform parameters, interpolation choices, passed-frame quality thresholds, frame-pair/case denominators, displacement/Jacobian extraction, and failure handling are absent. “At least four passed non-reference frames” is not machine-checkable until “passed” is defined.

Required revision: freeze the real CineMA adapter file/symbol and preprocessing/feature-hook contract; define slice/volume/time assembly and tensor shapes; define entropy/uncertainty; specify the complete SyN command/parameters, interpolation, transform/Jacobian receipts, pair- and case-level quality thresholds and denominators, failed-frame policy, and temporal input schema.

### 5.6 The matched pretrained/random control is not mechanically isolated

The plan correctly requires the same architecture, cases, frames, optimizer, budget, cadence, and selector, but “same seed” and “identically initialized downstream heads” are insufficient. Loading pretrained weights and instantiating a random source may consume RNG differently. The exact augmentation policy is also not defined. There is no common serialized downstream-initialization state/hash that both runs must load, nor a pre-run parameter-name/value comparison proving that the representation-source initialization is the only difference.

Required revision: define the exact augmentation pipeline and seed handling; create one common downstream projection/temporal initialization artifact with SHA; require both runs to load it; record parameter names, trainable/frozen sets, shapes, counts, initial hashes, optimizer configuration, cases, frames, cadence, and selection-rule hash; and fail before B5/B6 when any field other than representation-source initialization differs.

### 5.7 Validator and known-bad requirements are classes, not executable fixtures

The future validator paths are named, but their schemas and exact checks are not. `known_bad_classes` is only a list of labels: no fixture paths, payload schema, mutation applied, command, expected nonzero exit, or report path is specified. In particular, the plan does not name an executable fixture proving that a packet with seven T2-present edema-positive cases fails readiness. The current validators at the reviewed commit remain the weak validators rejected by the prior reviewer.

Required revision: enumerate every fixture path under `tests/route_B/known_bad/`, its mutation/schema, the exact validator command and expected failure key, and the aggregate self-test report. Add explicit fixtures for `<8` positive-edema cases, zero positive-edema GT, Pattern-SIP alias/no-gradient, OOF leakage, old-wrapper bypass, unmatched control, registered evidence not consumed, undertrained/pending/stale/inconsistent receipts, and every forbidden authority. B1 must have its own strict completion gate; old validator PASS cannot authorize B2 or training.

### 5.8 Stop states and continuation obligations are incomplete

The plan defines one controller completion token and forbidden authority tokens but does not provide a machine-readable set of allowed non-ready states, exact triggers, whether the controller must retry/monitor/return to an earlier phase, or when it may legally stop. This leaves the previous `SCIENTIFIC_UNDERTRAINED` early-stop failure structurally possible.

Required revision: define exact states and transitions for preflight failure, implementation failure, fewer than eight edema-positive cases, startup/runtime failure, pending/running/awaiting accounting, retry exhaustion, undertraining, missing aggregation, stale/inconsistent packet, unmatched control, and `CINEMA_CONTROL_UNRESOLVED`. Non-ready states must state the next required action and cannot request normal review while required execution/monitoring/aggregation remains.

### 5.9 Slurm preflight and durable finalizer are under-specified

The exact Python executable, partition order, walltime, mirror policy, and dependency semantics are acceptable. But there is no exact compute-node preflight task/command/output proving Python version, `torch` imports, CUDA visibility, optimizer construction, contract print, output/log/lock writability, and code/config/split hashes before B4. This is required by the Slurm skill after the prior bare-`python` failure.

The finalizer contract does not name the finalizer submission script/command, job-ID capture file, aggregation commands, log/lock/result paths, accounting retry fields, or how `afterany` is guaranteed over every attempt when B4/B5/B6 or B7 fails. Since B8 is modeled as depending on B7, a failure before B7 can leave no durable accounting finalizer.

Required revision: add an exact compute-node preflight node and receipt; define bounded same-scope retry limits and zero-credit rules; specify the finalizer submission command/script, job-ID ledger, `afterany` construction over all attempts, automatic `sacct` retries, aggregation commands and output files, mapper-final invocation, strict validator commands, Git-index heavy-artifact check, and local-commit boundary. The finalizer must run even when an upstream scientific phase fails.

### 5.10 Reviewer pass/fail is not machine-bound

The contract says the independent reviewer may accept an adequate negative packet and that reviewer acceptance authorizes later portfolio comparison, but it does not define exact reviewer decision tokens, required inputs, pass/revision/evidence/monitor criteria, or how candidate-ready differs from an adequate negative packet. The controller and reviewer would have to interpret this boundary.

Required revision: define the reviewer request path, pinned reviewed commit, exact required packet/validator/known-bad files, allowed reviewer tokens, exact rejection conditions, candidate-ready criteria, adequate-negative criteria, and authority boundaries. Reviewer acceptance must not imply upload, promotion, M11, hosted claims, cross-route merge, or final scientific resolution.

## 6. Items that already pass planning review

The revision should preserve the following strengths:

- Route B remains the full architecture route rather than the compressed Route A design.
- The four-scale sixteen-slot shared/private/interaction bank and two-pass spatial router are explicit.
- Pattern-SIP and OOF memory are required to be real train/forward paths, not summaries.
- Scar/edema proposals, soft ROIs, separate refiners, bounded correction, save/reload/export, and final-output interventions are retained.
- The previous no-positive-edema evaluation is explicitly repaired with pathology-balanced sampling and a minimum of eight T2-present edema-positive cases.
- CineMA provenance includes real URL, revisions, MIT license, and weight SHA; Cine is not deferred to future work.
- The intended pretrained/random comparison is same-architecture and downstream use remains bound to the clean-reloaded pretrained source.
- Training budgets, checkpoint schedules, selectors, metric gates, exact Python, `htzhulab`/`a100-gpu` routing, no V100, no-push, and forbidden authority actions are explicitly stated.

## 7. Decision

The plan has the correct scientific scope but still leaves data manifests, sampler semantics, Pattern-SIP/loss details, allowed source edits, the real CineMA adapter, matched-control initialization, validator fixtures, stop-state transitions, durable finalization, and reviewer pass/fail to the controller. This violates the Round02 handoff and the permanent no-blank-design hard gate.

`ROUTE_B_ROUND02_PLANNING_NEEDS_REVISION`

No Route B controller is authorized by this review. The revision token does not authorize code execution, training, Slurm submission, validation packaging/upload, route promotion, M11, hosted metric claims, cross-route merge, or a final scientific decision.
