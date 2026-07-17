---
route_id: route_B
portfolio_round: round03
date: 2026-07-18
role: planner
status: DRAFT_FOR_ROUND03_CRITIC_REVIEW
branch: route_B
remote_route_base_commit: f01427e72134d5e5be1bfd51b93bdefdd5f3126c
planner_main_base_commit: 6ed0a3bac82aa0ee8cb44250da0c2648965c6b42
final_planner_commit_binding: EXTERNAL_MAIN_HANDOFF_BINDS_FINAL_ROUTE_HEAD_AND_BLOBS
contract_path: prompts/routes/route_B.md
executor_plan_path: prompts/routes/route_B_executor_plan.yaml
critic_request_path: prompts/routes/route_B_critic_request.md
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_PROJECT_BACKGROUND_CURRENT_CONVERSATION
local_state_status: NOT_INSPECTED_BY_USER_INSTRUCTION
remote_binding_only: true
PROPOSAL_REFINER_RESEARCH_STATUS: READY_WITH_EXPLICIT_FALLBACK
PROTOTYPE_MEMORY_RESEARCH_STATUS: READY_WITH_EXPLICIT_FALLBACK
CINEMA_ADAPTER_RESEARCH_STATUS: READY_WITH_EXPLICIT_FALLBACK
REGISTRATION_TEMPORAL_RESEARCH_STATUS: TARGETED_CODE_PROBE_COMPLETED_FOR_PLANNING_CONTRACT
PLANNER_REVISION_READINESS: READY_FOR_INDEPENDENT_CRITIC_NOT_CONTROLLER
---

# Route B Round03 Planner audit

## Evidence baseline

The Planner read `main@6ed0a3bac82aa0ee8cb44250da0c2648965c6b42`, all mandatory governance/schema/helper files, the current Round02 handoffs, the permanent hard matrix, the Round02 comprehensive SRR evidence analysis, Deep Research commit `28c8aac80b7f18f3441c495dc9f2625fc10c460f`, the Route B Round02 Critic review, and the latest Route B route-local result/review/controller/completion/finalizer/implementation/validator/metrics/safety/mapper evidence.

The old packet is operationally informative but not scientifically inheritable: 25,000 steps and terminal race accounting were recorded, while formal evaluation had ten MyoPS cases, zero edema-positive GT cases, five Cine proxy cases, two scales, reduced slots, a legacy modality order, and insufficient semantic validators. No old ready token is inherited.

## Independent visual interpretation

SRR-v2 requires availability-aware modality evidence, selective retrieval, anatomy-guided proposal, pathology-specific refinement, and registered Cine temporal evidence. v2.5 separates scar/edema proposal and ROI geometry. v3 adds nnU-Net context/components/uncertainty, train/OOF prototypes, and bounded correction. The plan assigns evidence selection to stems/experts/routers/prototypes and lesion formation to proposal/ROI/refiner/final composition. This directly addresses the M9 finding that nonidentity dictionary changes can still worsen Dice, HD95, remote FP, and components.

## Targeted source/API probe

The exact first-party files requested by the Round03 prompt were read. Results entering the contract:

- canonical order is `[LGE,T2,C0]` in `anchors/myops_decode.py`;
- old Route B source uses `[LGE,C0,T2]` and is nonloadable for Round03;
- main proposal code exposes deterministic bootstrap provenance;
- current memory contains EMA/helper paths rather than the formal offline OOF bank;
- current CARE Cine adapter is a small convolutional model;
- current registration directly warps with `0.25*tanh(v)`;
- current temporal model consumes abstract `temporal_z`.

Pinned official CineMA code at commit `c10daa1d93f0ea28d8b9ad9206b0f673d25805c1` was read directly. `ConvUNetR` owns `decoder_dict` and `pred_head_dict`; the formal hook is the 32-channel `decoder_dict["sax"]` output before `pred_head_dict["sax"]`, followed by the Route B 32-to-16 projection. The ACDC config fixes spacing `[1,1,10]`, patch `[192,192,16]`, and four classes `background/RV/MYO/LV`. Official preprocessing symbols and class constants were recorded. Registration and temporal source gaps were therefore converted from `NEEDS_TARGETED_CODE_PROBE` to a concrete first-party replacement contract, not assumed existing APIs.

## Round02 Critic blockers closed

1. Every B0–B10 node has an exact prompt, command, unique result/runtime/log/lock/job namespace, required files, entry/success/failure states, completion token, and next state.
2. Deterministic manifest paths/generation, pretraining hash freeze, disjoint sampler precedence, replacement policy, ratio, seed, and runtime counts are fixed.
3. Expert topology, Pattern-SIP equation/groups/coefficients/schedule, full loss table, and training activations are numerical.
4. New work is route-local; shared first-party edits are prohibited and return to Planner.
5. CineMA class/hook/preprocessing/output contract, first-party SVF math, SyN parameters, pass thresholds, denominators, and temporal schema are exact.
6. One common serialized downstream initialization artifact and parameter-value inventory make pretrained/random isolation machine-checkable.
7. Known-bad classes are bound to B0/B1 executable fixture inventory and B2/B10 nonzero-exit self-tests.
8. Non-ready monitor/accounting/undertrained/resource/scientific/validator states and continuation obligations are explicit.
9. Every Slurm executor has compute-node preflight, bounded retry, afterok training, afterany finalization, per-attempt isolation, and terminal accounting.
10. Exact runtime reviewer tokens and their classification criteria are frozen in the contract and B10 prompt.

## No-blank-design check

No `TBD`, Controller-selected architecture, unspecified loss, arbitrary budget, unknown partition, unbound selector, or implicit failure branch is intended. Deterministic manifest SHA values are deliberately produced by B0 rather than guessed; their absence is a blocking state, not a design choice. Discovery of a required shared source edit is a Planner revision, not Controller discretion.

## Slurm/routing audit

All three partitions are planned. Full four-scale MyoPS stages use htzhulab/A100 and are V100-incompatible until exact unchanged-config peak memory is <=14.5 GiB; semantic downscaling is forbidden. V100 is assigned B2 lightweight gate, official CineMA extraction/matched controls, SyN/registration evaluation, selected reload/evaluation, and validator GPU tests. B7/B8 may use three-way race only after exact compatibility preflight; B3–B6/B9 use at most htzhulab+A100 two-way race. Distinct ready work has priority over duplicate race. Every race binds identical scientific hashes, isolated output/log/checkpoint/cache, atomic winner lock, loser zero credit, pending-loser cancellation, retry lineage, and finalizer coverage.

The plan preserves the Slurm skill requirements: explicit environment Python, one job <=8 hours, preflight on compute nodes, `afterok` training, `afterany` finalizer, scheduler blocker only after 12 two-hour checks/24 hours with no progress, and no monitor packet as completion.

## Mapper/fingerprint audit

B0/B1 bind source symbols and tensor/loss contracts. B2 captures forward/gradient/intervention/save-reload. Every stage records source/config/split/manifest/checkpoint hashes. B10 requires mapper final, route-local architecture fingerprint, architecture delta, heavy-artifact scan, strict validators, and lightweight commit before reviewer request. Root wiki remains unchanged until later Portfolio reconciliation.

## Static validator record

The plan was manually checked against current `executor_plan.schema.yaml` and `validate_executor_plan.py`: valid lanes, eleven distinct integer waves, all required fields, non-overlapping path namespaces, non-empty code-lane write scopes, earlier-wave dependencies, bounded retry fields, exact afterok/afterany values, mandatory preflight fields, and preflight/retry receipts inside each result directory.

The user explicitly prohibited shell/server execution, so actual exits are honestly recorded:

```text
route_B_executor_plan_validator: NOT_RUN_USER_PROHIBITED_SHELL
partition_race_validator: NOT_RUN_USER_PROHIBITED_SHELL
git_diff_check: NOT_RUN_USER_PROHIBITED_SHELL
remote_static_schema_review: PASS
```

The Critic request requires real zero exits on the exact bound commit before a ready token. Thus `PLANNER_REVISION_READINESS` means ready for independent Critic, not ready for Controller.

## Source, history, and research files read

Main governance, schema, route, watchboard, history, Slurm, mapper, executor helper, and finalizer files; Round02 planner/Critic files; Route B latest route-local packet and validators; first-party SRR/proposal/memory/loss/ROI/Cine/registration/temporal sources; official CineMA pinned `convunetr.py`, ACDC config/preprocess/constants; and all three Project SRR images.

## Deadline checkpoints

- July 20: B0–B2 terminal implementation gate.
- July 21: evidence warmup and proposal gate.
- July 22: refiner/joint first formal MyoPS evidence plus official CineMA/control progress.
- July 23: only evidence-directed same-scope repair.
- July 24: science/loss freeze.
- July 25: packet and independent review input.
- July 26–27: no new architecture/science.

## Authority and remote-state boundary

Per user instruction, no local worktree, server, or unpushed state was inspected. This audit binds remote evidence only. The final main handoff will bind the actual final Route B commit and blobs; self-embedding that commit in the audit would be circular.

No Controller is authorized by this audit. No validation upload, promotion, M11, cross-route merge, hosted claim, or final scientific decision is authorized.