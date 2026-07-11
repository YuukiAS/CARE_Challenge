---
task_key: 20260711_srr_v3_m10_complete_mechanism_repair
milestone_id: M10
role: critic
reviewed_prompt_path: prompts/shared/EXECUTOR_PROMPTS.md#M10 executor/controller: SRR-v3 complete mechanism repair
reviewed_contract_sha256: 677b5e42f070175986e2cbf5598eb3b2c1bc872ea85349c90f3611fe2cd8150c
reviewed_staging_path: prompts/shared/M10_srr_v3_complete_mechanism_repair.md
canonical_reviewer_prompt_path: prompts/shared/REVIEWER_PROMPTS.md#M10 reviewer: SRR-v3 complete mechanism repair
canonical_contract_sha256: 5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64
planner_draft_commit: 828735482396d6d727d2294e88c89868e3118ad3
critic_decision: READY_FOR_CODEX_MERGE
critic_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
reviewed_at: 2026-07-11T10:18:26Z
files_read: [START_HERE_FOR_GPT.md, GPT_PLANNER_CARE_PROTOCOL.md, AGENTS.md, prompts/AGENT_FLOW_V2_PROTOCOL.md, prompts/HANDOFF_GATE_POLICY.md, prompts/GPT_HARD_GATE_PROMPT.md, prompts/MILESTONE_REVIEW_PROTOCOL.md, prompts/schemas, wiki root, wiki/current_state.yaml, wiki/history/M09, M09 result packet and review, latest Planner staging and executor plan, superseded Critic staging and planning review, SRR-v2, SRR-v2.5, SRR-v3, baseline technical report]
blocking_findings: [superseded planner baseline, missing Planner ancestry, executor-count conflict, incomplete exact router and output equations, under-specified mature registration thresholds, incomplete matched controls, stale planning token]
---

# M10 latest-Planner reconciliation and independent planning review

## Review target and lineage correction

The previous critic review was invalid for integration because it recorded
`planner_draft_commit: e26895b99dc142ff64ea6e6f291600c6b67af98c`. Remote synchronization found a later Planner branch and draft:

```text
default branch: main
pre-reconciliation default HEAD: 925a00169649a523947e475204e68228cb8816f6
Planner branch: agent/m10-planner-draft
Planner HEAD: 828735482396d6d727d2294e88c89868e3118ad3
Critic branch: agent/m10-planning-critic-repair
pre-reconciliation Critic HEAD: 435abf35a4b1b85d75e58f83bcb58faa0b89efe1
pre-reconciliation common merge-base: 925a00169649a523947e475204e68228cb8816f6
staging: prompts/shared/M10_srr_v3_complete_mechanism_repair.md
post-merge canonical executor section: prompts/shared/EXECUTOR_PROMPTS.md#M10 executor/controller: SRR-v3 complete mechanism repair
post-merge canonical reviewer section: prompts/shared/REVIEWER_PROMPTS.md#M10 reviewer: SRR-v3 complete mechanism repair
executor plan: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_executor_plan.yaml
planning review: prompts/tasks/20260711_srr_v3_m10_complete_mechanism_repair_planning_review.md
```

The existing Critic branch was rebased by ref to the latest Planner HEAD before reapplying critic changes. The staging was then explicitly placed in `PLANNING_REVIEW_RUNNING` with empty review token and reviewed commit. The old token was not carried forward. The final branch must make `828735482396d6d727d2294e88c89868e3118ad3` an actual ancestor; changing only this review's SHA would not satisfy the gate.

## Independent evidence reread

I reread the current protocol and schemas, the dynamic M09 predecessor selected by `wiki/current_state.yaml`, every M09 component history page, the M09 result/review evidence, the latest Planner staging and three-executor plan, and the superseded Critic contract. I also rechecked the SRR-v2/v2.5/v3 diagrams. The recovered objective remains availability-aware spatial retrieval through a real shared/private/interaction dictionary, anatomy-guided pathology proposal, negative-space/prototype memory, pathology-specific soft-ROI refinement, SRR-owned final logits, and a registration-gated learned Cine temporal output. `nnU-Net` remains baseline/context/teacher/safety only.

The latest Planner draft is materially stronger than the old baseline: it adds three serial responsibility-separated executors, a D0-D3 retrained design ladder, full 44-case scheduled evaluation, explicit CineMA adaptation, pair-valid MyoPS feature alignment, fifteen blocking result directories, and a 72,000-second aggregate training floor. These are valid Planner-only requirements and are retained.

## Three-way reconciliation ledger

| Area | Latest Planner-only content | Superseded Critic-only content | Agreement or conflict | Final retained contract and reason |
|---|---|---|---|---|
| Lineage/gate | Three-executor draft at `8287354`; empty critic metadata | Review/token/hash bound to old `e26895b` baseline | Direct conflict | Latest Planner commit is the true baseline and ancestor; old review is superseded; new stable hash/review/binding are required. |
| Executor count | `executor_count: 3`, waves for shared architecture, MyoPS, Cine | `executor_count: 1` for continuity | Conflict | Keep 3 serial executors with `executor_slots=max_parallel=1`. Their write scopes are genuinely disjoint by responsibility and prevent wave-2 hot patches; controller remains sole merge/continuity owner. |
| Wave duties | Wave 1 implementation/fidelity; wave 2 D0-D3 MyoPS; wave 3 CineMA/registration/temporal | One executor owned all code/jobs | Conflict but resolvable | Preserve Planner waves and strengthen freeze/return-to-wave-1 rules. MyoPS and Cine never run in parallel. |
| Dictionary designs | D0 static matched, D1 spatial BR2, D2 hierarchical PSIP, D3 memory PropRef, all retrained | One full candidate plus matched no-dictionary/no-context controls | Compatible | Keep D0-D3 as the parameter-matched causal ladder; retain no-context retrain, hard-negative refresh, and alignment control. No inference-only substitute. |
| Slot bank | At least 4 shared, 2 per private and 2 per pair interaction | Exact expert blocks and stricter invalid-slot threshold | Compatible, Planner minimum was not exact | Fix exactly 16 slots per scale: 4 shared, 6 private, 6 pair interaction; exact independent residual block and `max_invalid_weight<=1e-8`. |
| Router | Two-pass lesion-conditioned spatial router; staged soft/top-k schedule | Exact entmax query shapes, temperature and final-output gradient path | Compatible | Keep two-pass router and proposal feedback; use entmax1.5, `1.5→0.7`, staged soft/top-4/top-2, center forbidden as input. |
| Pattern-SIP | Participation-ratio group integrativeness, nonuniform load, collapse prevention | Explicit group/load equations and independent gradient/alias tests | Compatible | Keep participation-ratio PSIP with availability/style/hard groups and target mass 0.50/0.35/0.15; independent function, tensor and gradient evidence. |
| Prototype/memory | Three-fold cross-fitted EMA+learnable residual, category memory, hard-negative refresh | Exact slot counts, OOF isolation, similarity and margin definitions | Compatible with different detail | Use four deterministic train-only OOF shards, exactly 8 positive/12 negative slots per pathology, EMA plus bounded trainable residual, FIFO provenance, safe hard negatives. Four shards give stricter case isolation while preserving Planner cross-fitting. |
| Proposal/refiner | Learnable nonnegative coefficients, teacher cap, soft ROI and anatomy fallback | Fixed proposal coefficients, uncertainty equation, exact refiners and normalized six-class output | Conflict over learned versus fixed coefficients | Fix the coefficients in M10 to remove executor tuning discretion and preserve causal comparability. Keep Planner teacher cap and contribution maps. Final probabilities are normalized SRR proposal/refinement outputs; no anchor identity or silent fallback. |
| no-T2 | Loss/memory/decode/export blocking | Exact zero edema probability and no positive/negative updates | Agreement | Retain four-point blocking; synthetic T2 dropout also disables edema supervision, never creates negatives. |
| Anatomy/alignment | Union/LV/RV prior; D3 pair-valid LGE-reference alignment control | Exact soft gate/distance and stronger learned-registration QC | Compatible | Keep differentiable soft anatomy, detached EDT branch, pair-valid MyoPS alignment as a required trained control, not a universal raw-image registration base. |
| MyoPS budget | D0-D3 + refresh + no-context + alignment; 72,000 seconds, 44 cases, 16 T2-positive, CenterB/C minima | Larger per-control step floors and explicit optimizer/early-stop/stability | Compatible after strengthening | Preserve 72,000 seconds and 44-case evaluation; set aggregate steps to 220,000 and validation events to 120; every run has independent step/time/full-case/early-stop floors. |
| Checkpoint/control | Scheduled 44-case lexicographic Pareto selection and D0-D3 retrains | Explicit challenge-facing score, eligibility and prediction sanity | Compatible | Keep Planner's worst-group-first lexicographic gate, augmented with eligibility, prediction volume, cache/split/decode hashes, and pathology-specific gates. |
| Component attribution | Same-checkpoint interventions plus D0-D3/no-context/refresh matched controls | Explicit component states distinguishing no call/no gradient/no output effect/no benefit | Compatible | Retain both. A CSV alone is never implementation; `MECHANISM_NO_SIGNAL_AFTER_ADEQUATE_MATCHED_TEST` requires adequate retraining and clean output intervention. |
| CineMA | Formal provenance, CARE adapter, partial unfreezing/adapter, random-init control | No equivalent external-backbone requirement | Planner-only valid content | Retained as blocking provenance/adapter lane. Unverifiable license/checksum blocks; frame0 mask export is not completion. |
| Cine registration | Learned diffeomorphic registration, >=8 frames, classical controls, failures retained | Exact 3D U-Net, scaling-and-squaring, loss weights and numerical QC thresholds | Compatible but Planner gate was qualitative | Fix channels `[16,32,64,128]`, 7 integration steps, symmetric transforms, exact LNCC/anatomy/smooth/Jacobian/inverse loss, >=12 cases/60 pairs and quantitative folding/overlap/cycle gates. |
| Cine temporal | Cue-specific temporal dictionary and same-subset controls | Exact eight slots, QC masking, output/loss equations | Compatible | Retain exactly eight temporal slots and learned ED-space output; fewer than four valid non-reference frames is a registration failure, not frame0 fallback. |
| Slurm continuity | Three wave finalizers, global all-job finalizer, 24-hour saturation threshold | Two-stage `FINALIZER_A/B`, retryable accounting and no monitor completion | Agreement | Keep per-wave `afterany` receipts plus controller-global `afterany` over every job ID; terminal accounting, aggregation, mapper final, validators, one local lightweight commit. |
| Wiki/history | Root wiki updates, pre-review M10 snapshot/delta, M08/M09 immutable | `candidate_unreviewed`, current_state remains M09 until review reconciliation | Compatible | Retain both; mapper creates M10 candidate snapshot and figures but cannot advance current state or invent review token. |
| Reviewer | Independent read-only audit of 15 dirs/3 receipts and all formal runs | Expanded rejection states and no promotion authority | Compatible | Reviewer remains separate, read-only, post-commit. Adequate negative results are no-promotion/scientifically unresolved, not scientific stop. |

## Executor-count decision

The final decision is **three executors in three serial waves**, not one executor and not three parallel workers:

```text
wave 1  m10_shared_architecture_executor
        shared MyoPS architecture/loss/config/tests/fidelity only
wave 2  m10_myops_training_executor
        frozen architecture; D0→D1→D2→D3→refresh→no-context→alignment→causal audit
wave 3  m10_cine_temporal_executor
        CineMA provenance/adapter→learned registration gate→learned temporal output
```

`executor_slots: 1`, `max_parallel: 1`, explicit dependencies, isolated worktrees/branches/result/runtime/log/lock paths, deterministic merge order, and controlled completion tokens remain mandatory. This preserves the Planner's responsibility isolation without violating the default sequential MyoPS-before-Cine rule. It also prevents the training executor from modifying the model after formal runs expose an inconvenient result.

## Final scientific contract relative to latest Planner

The final contract preserves all material Planner-only content: D0-D3 design competition, 44-case metric-facing selection, pair-valid alignment control, CineMA formal adaptation, three serial waves, 15 exact evidence directories, all-job continuity, and pre-review Wiki/history snapshot.

Critic changes make previously open choices executable rather than replacing the Planner route:

- exact tensor shapes, 16-slot bank and residual expert block;
- exact two-pass entmax router and staged sparsity schedule;
- exact Pattern-SIP/load targets and alias tests;
- exact OOF memory inventory, update and safe-negative policy;
- fixed proposal coefficients, uncertainty, soft ROI, pathology refiners, and six-class probability relation;
- exact optimizer, loss stages, early-stop floors, stability and resume provenance;
- aggregate `220000` optimizer steps, `72000` effective train-loop seconds and `120` validation events;
- exact learned-registration architecture, objective and multi-case Jacobian/anatomy/inverse-consistency gate;
- exact eight-slot temporal dictionary and final-output intervention;
- fail-closed component-state, validator, finalizer, Wiki and reviewer contracts.

No unresolved scientific conflict remains. Registration and Cine can fail at runtime, but their implementation, adequate training and evidence cannot be skipped. Negative adequate results remain no-promotion evidence.

## Contract binding and decision

The stable pre-merge staging contract hash was recomputed using `scripts/validation/hash_milestone_contract.py`:

```text
677b5e42f070175986e2cbf5598eb3b2c1bc872ea85349c90f3611fe2cd8150c
```

After Codex planning integration deletes the standalone staging file, runtime controllers must validate the merged canonical prompt sections instead of hashing the deleted staging path. The post-merge canonical section hash is:

```text
5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64
```

It is computed by:

```bash
python scripts/validation/hash_canonical_prompt_contract.py \
  --executor-file prompts/shared/EXECUTOR_PROMPTS.md \
  --executor-heading 'M10 executor/controller: SRR-v3 complete mechanism repair' \
  --reviewer-file prompts/shared/REVIEWER_PROMPTS.md \
  --reviewer-heading 'M10 reviewer: SRR-v3 complete mechanism repair'
```

The reviewed-contract commit must contain the final staging, executor plan and this review. A subsequent metadata-only commit must set `planning_reviewed_commit` to that reviewed-contract commit, never to the metadata commit itself. The metadata field is excluded from the stable pre-merge hash. The canonical post-merge hash is the runtime binding after staging cleanup.

```text
critic_decision: READY_FOR_CODEX_MERGE
critic_token: PLANNING_CRITIC_READY_FOR_CODEX_MERGE
```

This decision authorizes only Codex planning integration and candidate validation. It does not execute M10, create runtime results, merge the default branch, package/upload validation, promote a route, or start M11.
