---
route_id: route_B
route_name: "Route B — full SRR-v3 architecture implementation"
branch: route_B
worktree: /users/a/e/aereinh/CARE_worktrees/route_B
status: PLANNER_DRAFT_FOR_CRITIC
not_a_milestone: true
planner_base_commit: dfea8e1bb22de1bbcf3ff062359f1dd086f56c38
diagram_source: "ChatGPT Project background materials / current conversation visual channel"
diagram_versions_read:
  - SRR-v2
  - SRR-v2.5
  - SRR-v3
visual_read_status: READ_FROM_PROJECT_BACKGROUND_OR_CURRENT_CONVERSATION_UPLOAD
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
  - M11_AUTHORIZED
  - FINAL_SCIENTIFIC_CONCLUSION
---

# Route B planning contract

Route B is not a milestone. It is the isolated route for implementing and validating the complete SRR-v3 architecture before any formal training. It must prove the diagram modules exist as executable code paths that affect final logits/labels, not just as configs, wrappers, tables, or diagrams.

## Recovered SRR objective from visual diagrams

The SRR v2/v2.5/v3 diagrams show a full segmentation-native selective retrieval framework. It starts from LGE/C0/T2 with explicit availability, uses modality-specific stems and availability-aware routers, retrieves from shared, modality-private and optional interaction dictionaries with real prototype groups, generates anatomy-guided scar/edema proposals from union/LV/RV/anatomy-distance/uncertainty/context, refines scar and edema through pathology-specific soft-ROI refiners, and in v3 preserves a strong nnU-Net anchor through bounded residual correction. Cine is a registration-aware anatomy-first temporal retrieval branch that must consume ED/reference, key frames, registration/warping, anatomy/features/uncertainty and temporal aggregation.

## Route objective

Route B must convert SRR-v3 from architecture diagram into a complete, auditable implementation. Its first success criterion is not leaderboard score; it is implementation fidelity:

```text
code completion -> real case forward -> finite nonzero losses -> gradients to target modules -> intervention changes final logits/labels -> save/reload consistency -> export/layout QA -> implementation freeze -> only then formal training
```

Route B must not start formal training until this chain passes.

## Branch, worktree, namespaces

| item | value |
| --- | --- |
| branch | `route_B` |
| worktree | `/users/a/e/aereinh/CARE_worktrees/route_B` |
| controller tmux | `care_route_B_controller` |
| reviewer tmux | `care_route_B_reviewer` only after controller packet commit |
| result root | `results/route_B/` |
| runtime root | `results/route_B/runtime/` |
| log root | `logs/route_B/` |
| lock root | `results/route_B/locks/` |

## Exact write scopes for the future controller

Allowed branch-local write scopes:

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

Forbidden writes:

- `prompts/shared/**` unless a later portfolio-level instruction explicitly authorizes canonical prompt merge;
- `results/route_A/**`, `results/route_C/**`, `logs/route_A/**`, `logs/route_C/**`, `routes/route_A/**`, `routes/route_C/**`;
- root `wiki/current_state.yaml` and `wiki/history/**` before final portfolio reconciliation;
- validation upload package directories, hosted submission zips, raw data, checkpoints, NIfTI predictions, large logs, secrets.

A Route B mapper may write route-local architecture receipts inside `results/route_B/`; it must not rewrite root current state before independent review and portfolio reconciliation.

## MyoPS architecture contract

Route B must plan and implement all of these MyoPS modules as real code paths:

1. modality-specific stems for LGE, C0/bSSFP, and T2;
2. availability-aware router that reads both the availability mask and image-derived pooled features;
3. multi-scale shared dictionary `D_sh`;
4. LGE-private, C0-private and T2-private dictionaries;
5. optional interaction dictionary, guarded by an implementation flag and tested as on/off intervention;
6. real prototype memory or OOF prototype bank with scar-positive, scar-safe-negative, edema-positive and edema-safe-negative definitions;
7. anatomy decoder producing union, LV and RV/anatomy-context maps;
8. scar proposal decoder, LGE-dominant and high-precision;
9. edema proposal decoder, T2-conditioned and broader-context;
10. soft-ROI generator with anatomy prior, distance, uncertainty and nnU-Net confidence/context;
11. scar soft-ROI refiner;
12. edema soft-ROI refiner;
13. bounded nnU-Net residual correction with help/harm gate and anchor fallback;
14. final label/export path with compact-to-raw CARE semantics checked;
15. save/reload/resume/export support.

The full loss plan must include anatomy, scar proposal, edema proposal, scar refinement, edema refinement, residual/gate, negative-space/hard-negative, dictionary/prototype regularization, prior/ROI regularization, and optional alignment loss. The executor may stage losses progressively, but formal training cannot start until every required loss is either implemented and gradient-tested or explicitly disabled by a Critic-approved revision.

## Cine architecture contract

Route B must plan and implement a real Cine route, not just topology postprocessing. Required modules:

1. real CineMA or approved anatomy source loader with provenance, weights/license record, and random-init control if pretrained is used;
2. frame-wise anatomy logits, features and uncertainty;
3. ED/reference detection and selected key-frame policy;
4. registration interface with actual warp outputs;
5. if learned registration is used: symmetric velocity, scaling-and-squaring, Jacobian, inverse consistency and registration losses must be real, not proxy-only;
6. ANTs/SyN or comparable classical registration control when learned registration is not ready;
7. temporal representation dictionary with frame-quality or motion-saliency routing;
8. temporal aggregation/refiner that consumes registered anatomy/features/motion/uncertainty;
9. checkpoint/resume/export/layout QA.

Cine readiness requires a multi-case before/after matrix showing temporal module enabled vs disabled and registration evidence. Frame0-only, descriptor-only, topology/LCC-only, untrained VoxelMorph, or optical-flow-only proxy without registration evidence must fail.

## Implementation-before-training gate

Formal training is forbidden until the following pass on real cases.

### MyoPS checks

- LGE-only, LGE+C0 and LGE+C0+T2 real forward paths;
- missing modality tensors are absent/masked and do not enter as real observed images;
- router reads availability plus pooled image features;
- each dictionary/prototype group has a real source, initialization, and train/OOF provenance;
- anatomy, proposal, soft-ROI, refiner and residual modules are all in the forward path;
- disabling each major module changes final logits/labels or a documented route-specific output;
- losses are finite, nonconstant and nonzero where expected;
- gradients reach stems, router, dictionary/prototypes, anatomy, proposals, refiners and residual gate;
- no-T2 edema loss is zero/masked for no-T2 samples;
- save/reload output consistency passes;
- export maps to official labels and records voxel/hash comparisons.

### Cine checks

- real multi-frame input consumed;
- real anatomy logits/features/uncertainty loaded/computed;
- registration or fixed/SyN warp produces traceable transform files/statistics;
- temporal dictionary/refiner consumes registered anatomy/features/motion/uncertainty;
- temporal module on/off changes final output on more than one case or writes honest blocker;
- resume does not reset temporal state;
- output maps to official submission layout.

### Implementation freeze

After the implementation gate passes, freeze code/config hashes for the first formal train/eval wave. Any architecture or loss formula change after freeze requires a new implementation-gate run and Critic-visible revision.

## Training/evaluation gate after implementation passes

Route B training is allowed only after implementation freeze. First training wave must be bounded and attributable:

- job budget <= 8 hours unless later Critic/controller packet authorizes a specific longer run;
- report optimizer steps, train-loop seconds, validation events, prediction sanity, loss behavior and cache isolation;
- same-split nnU-Net anchor comparison is required;
- report modality groups, T2-present/GT-positive edema, no-T2 empty-GT safety, CenterB/CenterC where available, scar-positive cases, remote-FP/component/HD95 and volume-ratio guardrails;
- do not use smoke-scale or undertrained evidence for route promotion or final scientific stop.

## Slurm and partition plan

Use `htzhulab` first, `a100-gpu` second, and `volta-gpu` only when V100 compatibility is explicitly declared without changing science semantics. Multiple independent ready jobs should use different partitions rather than duplicate races. A three-way race is allowed only for a single critical pending job with identical scientific semantics, isolated attempts, shared atomic winner lock, loser receipts, and cancellation of pending losers.

Pending/running/monitor/`AWAITING_SACCT` states are not completion. The controller/finalizer must rerun aggregation after job completion and commit tracked lightweight evidence.

## Expected result packet

The Route B controller must produce a lightweight packet under `results/route_B/` with at least:

- `result.md`
- `implementation_gap_inventory.md`
- `architecture_component_trace.csv`
- `implementation_gate.md`
- `implementation_gate.json`
- `gradient_and_intervention_report.csv`
- `save_reload_export_report.json`
- `cine_registration_temporal_report.csv`
- `commands_run.md`
- `controller_report.md`
- `completion_check.md`
- `review_request.md`
- `MANIFEST.md`

Training/eval files such as `metrics_summary.csv`, `case_safety_matrix.csv`, and `training_adequacy.csv` are required only if formal train/eval actually runs after implementation freeze. Missing train/eval is acceptable only as `SCIENTIFIC_UNDERTRAINED` or `NEEDS_EVIDENCE`, not as completion of the scientific route.

## Validator known-bad cases

Route B validators must fail closed on:

- any required SRR-v3 module represented only by placeholder, mock, dataclass, static config, CSV-only diagnostic, fake URL/hash, or no-op wrapper;
- old nnU-Net or old Cine wrapper bypass of final outputs;
- forward pass without availability-aware routing;
- dictionary/prototype groups with no real train/OOF provenance;
- proposal/refiner/residual modules that do not affect final logits/labels;
- no-T2 edema negative supervision;
- Cine frame0-only, descriptor-only, topology-only, proxy registration, untrained VoxelMorph, or temporal module not consuming registered evidence;
- formal training before implementation gate and save/reload/intervention checks;
- pending Slurm/monitor packet as completion;
- validation upload, route promotion, final scientific conclusion, M11, or cross-route merge.

## Reviewer checklist

The Route B reviewer must be independent and read-only. It must check:

- each SRR-v3 diagram module is mapped to code path, runtime evidence, and unresolved gap;
- implementation gate ran before formal training;
- on/off interventions alter final logits/labels;
- gradients reach target modules;
- save/reload/export are consistent;
- Cine has real registration/temporal evidence or honest blocker;
- `training_adequacy.csv` does not promote smoke-scale evidence;
- controller stopped before route promotion/upload/M11.

## Stop/continue criteria

Continue after implementation gate only if full SRR-v3 modules are real and first evidence is adequate. Stop with `NEEDS_REVISION` if architecture is incomplete or modules are mock/no-op. Stop with `SCIENTIFIC_UNDERTRAINED` if implementation is real but training evidence is too small. Stop with `NEEDS_EVIDENCE` if required runtime artifacts are missing.

## Finalizer behavior

Finalizer must perform terminal Slurm accounting, aggregation, strict validators, architecture trace validation, `git diff --check`, packet manifest, local lightweight commit, and then stop. It must not write `review.md`, push, upload validation, start Route A/C, start M11, or claim route promotion.

## Prompt/shared policy

This planner draft intentionally does not modify `prompts/shared/`. Route B must keep shared prompts unchanged unless a later portfolio-level instruction explicitly requests canonical prompt integration.
