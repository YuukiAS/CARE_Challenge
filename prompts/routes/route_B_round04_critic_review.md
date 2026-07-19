---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: independent_planning_critic
status: PLANNING_NEEDS_REVISION
reviewed_main_commit: 403ee56f97fbe62edd5c940f8357b21ebf4e64e8
reviewed_route_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
main_target_match: true
route_evidence_target_match: true
planner_plan_blob: b24695f2aa85b6fdeb91053533fedba66548eee5
controller_contract_blob: 74877d513f73dd39625f127a4ea464d67f18b599
executor_plan_blob: a31112ae1d65e8f46e67786b46913f97935bf95e
critic_request_blob: 8bede6942793c570bb7d60b882aefea0b3a17429
planner_audit_blob: 91ddff187f5f003917aed0d8417b58d098392b71
planner_prompt_blob: de222d2b2e65d89b59efcfbd82620652d67ca96a
all_planning_blobs_match: true
diagram_versions_read: [SRR-v2, SRR-v2.5, SRR-v3]
visual_read_status: READ_FROM_CURRENT_CONVERSATION_PROJECT_MATERIALS
round03_evidence_reviewed: true
round03_stage_interpretation: B3_ADEQUATE_NEGATIVE_NOT_FULL_ROUTE_NEGATIVE
remote_scientific_contract_review: PASS_WITHOUT_DOWNGRADE
remote_semantic_blank_authority_review: PASS
remote_forbidden_path_review: PASS
remote_bare_formal_python_review: PASS
local_users_worktree_available: false
git_fetch_exit_code: 128
git_status_exit_code: 128
git_rev_parse_exit_code: 128
executor_plan_validator_exit_code: 1
git_diff_check_exit_code: 1
pyyaml_contract_check_exit_code: 1
semantic_scan_exit_code: 1
forbidden_path_interpreter_scan_exit_code: 1
hard_blockers:
  - CURRENT_NOT_ADVANCED_TO_ROUND04
  - B10_TERMINAL_FINALIZER_UNREACHABLE_ON_EARLY_TERMINAL_BRANCHES
  - PER_EXECUTOR_VALIDATOR_COMMANDS_NOT_MACHINE_BOUND
  - REQUIRED_USERS_EXECUTABLE_CHECKS_NOT_EXIT_ZERO
controller_start_authorized: false
validation_upload_authorized: false
route_promotion_authorized: false
m11_authorized: false
cross_route_merge_authorized: false
hosted_metric_claim_authorized: false
final_scientific_decision_authorized: false
decision_token: ROUTE_B_ROUND04_PLANNING_NEEDS_REVISION
---

# Route B Round04 Independent Planning Critic Review

## 1. Scope

This was a planning-only review. No Controller or tmux session was started. No implementation, model training, Slurm submission or monitoring, runtime `review.md`, validation packaging/upload, route promotion, M11, cross-route merge, hosted-metric claim, or final scientific decision was performed.

The review is bound to exact main commit `403ee56f97fbe62edd5c940f8357b21ebf4e64e8` and exact Route B evidence commit `b9c7664da7cb1f1892fff37a4497722f31a0a96d`.

## 2. Exact binding result

Immediately before writing this review, remote `main` and `route_B` were re-fetched through the authenticated GitHub source and were identical to the requested targets. The six Round04 planning blobs also matched exactly:

| file | required blob | observed result |
|---|---|---|
| `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md` | `b24695f2aa85b6fdeb91053533fedba66548eee5` | MATCH |
| `prompts/routes/route_B_round04_controller_contract.md` | `74877d513f73dd39625f127a4ea464d67f18b599` | MATCH |
| `prompts/routes/route_B_round04_executor_plan.yaml` | `a31112ae1d65e8f46e67786b46913f97935bf95e` | MATCH |
| `prompts/routes/route_B_round04_critic_request.md` | `8bede6942793c570bb7d60b882aefea0b3a17429` | MATCH |
| `prompts/routes/route_B_round04_planner_audit.md` | `91ddff187f5f003917aed0d8417b58d098392b71` | MATCH |
| `prompts/routes/route_B_round04_planner_prompt.md` | `de222d2b2e65d89b59efcfbd82620652d67ca96a` | MATCH |

The target is therefore not stale. The revision decision below is based on substantive and executable hard gates.

## 3. Sources and independent visual review

The required main governance files, Agent-Flow protocol, handoff gates, anti-laziness protocol, persistent route matrix, route entrypoints, Slurm skill, mapper skill, root wiki, current-state/history entries, six Round04 planning files, and exact Round03 Route B packet/reviewer evidence were read.

SRR-v2, SRR-v2.5, and SRR-v3 were independently read through the current Project/current-conversation visual channel. The recovered invariant route is:

```text
observed LGE/T2/C0 only, with explicit availability
-> four-scale modality-specific evidence
-> shared/private/interaction retrieval
-> anatomy-guided scar and edema proposals
-> pathology-specific soft ROI and separate refiners
-> bounded final correction over an nnU-Net anchor/context source
-> official-label reconstruction and final-output intervention
```

The Cine branch requires official per-frame anatomy logits/features/uncertainty, reference-space registration, motion/Jacobian/quality evidence, and registered temporal aggregation. A single-frame wrapper or proxy is not faithful.

## 4. Round03 evidence interpretation

The Round04 Planner interpretation of Round03 is correct.

Round03 B3 reached `43003` optimizer steps, `1800.7964860140346` train-loop seconds, and `22` validation events. It passed finite-loss, loss-decrease, exact `E,E,S,R` sampling, invalid-slot-zero, and no-T2 edema-zero checks. It failed `anatomy_union_overfit`.

B4, B5, B6, B7, B8, and B9 did not execute. The Round03 Reviewer explicitly accepted the B3-blocked terminal packet with `ROUTE_B_ROUND03_REVIEW_ADEQUATE_NEGATIVE`; it did not establish a full Route B scientific stop. The Round03 Controller report also retained `route_negative_decision: NOT_REVIEWED` and `scientific_resolution_status: AWAITING_REVIEW`.

Therefore:

- the Round03 token may be inherited as an adequate negative for the B3 evidence-warmup gate;
- it cannot be used as evidence that proposal, refiner, joint MyoPS selection, official CineMA matched control, faithful registration, or temporal aggregation failed;
- B4-B6 and B7-B9 require new execution after a corrected implementation/readiness gate.

This part of the Round04 plan passes.

## 5. Scientific contract assessment

The Round04 scientific contract does not reduce Route B to Route A, nnU-Net-only, wrapper-only, postprocess-only, validator-only, or a two-scale shortcut. It preserves and numerically binds:

- canonical `[LGE,T2,C0]` inputs and explicit availability without zero-fill availability inference;
- four scales `[32,64,128,256]` and sixteen experts per scale;
- spatial/pathology-conditioned two-pass routing and invalid-slot limits;
- numerical Pattern-SIP and its coefficient schedule;
- four-shard OOF-fitted, inference-frozen prototypes;
- training-only safe hard-negative queues with no-T2 edema exclusion;
- corrected union/LV/RV anatomy targets and strict two-case train-only micro-overfit;
- separate scar and edema proposals, soft ROI geometries, and refiners;
- bounded final correction and real final-output interventions;
- B3 as representation readiness, B4/B5 continuation, and B6 as the first full MyoPS classification stage;
- a B7-B9 Cine lane independent from B3 after B2;
- official CineMA source/commit/revision/license/weight SHA, multiclass logits/features/uncertainty, and matched random control;
- seven-step SVF, true Jacobian, inverse composition, real SyN, and registered temporal inputs;
- same-split nnU-Net baseline, case-wise help/harm, required hard subgroups, full ablation, clean reload, and official-label round trip;
- minimum effective training budgets and zero-credit failed/partial attempts;
- `htzhulab` default, isolated `htzhulab+a100-gpu` long-wait races, and V100 credit only for unchanged scientific configuration with peak memory at most `14.5 GiB`;
- Controller responsibility through terminal accounting, post-completion aggregation, mapper final, strict validation, local lightweight packet commit, and reviewer handoff;
- all forbidden downstream authorities.

No explicit `TBD`, unbounded `optional`, `as appropriate`, `if needed`, `choose best`, `Codex decide`, `controller decide`, `future work`, Cine deferral, `/overflow/htzhu/CARE`, or formal bare-`python` design was found in the remote planning content. The scientific and routing direction can be retained in the revision.

## 6. Mandatory executable checks

The required native worktree was not mounted in this Critic runtime. The actual command outcomes were:

```text
CHECK=git_fetch
cd /users/a/e/aereinh/CARE && git fetch --all --prune
EXIT=128
reason: /users/a/e/aereinh/CARE does not exist in this runtime

CHECK=git_status
cd /users/a/e/aereinh/CARE && git status --short --branch
EXIT=128

CHECK=git_rev_parse
cd /users/a/e/aereinh/CARE && git rev-parse HEAD origin/main origin/route_B
EXIT=128

CHECK=executor_plan_validator
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_round04_executor_plan.yaml
EXIT=1
reason: required worktree was unavailable before the validator could run

CHECK=git_diff_check
git diff --check
EXIT=1
reason: required worktree was unavailable

CHECK=pyyaml_contract
assert executor_count == 11
assert max_parallel == 2
assert required_planning_review_token == ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER
EXIT=1
reason: required worktree was unavailable

CHECK=semantic_scan
TBD|optional|as appropriate|if needed|choose best|Codex decide|controller decide|按需|视情况|自行决定|future work|defer
EXIT=1
reason: required worktree was unavailable

CHECK=forbidden_path_interpreter_scan
/overflow/htzhu/CARE and bare formal python
EXIT=1
reason: required worktree was unavailable
```

Remote content inspection confirms that the YAML header states `executor_count: 11`, `max_parallel: 2`, and the required planning token. The Planner audit also records a prior validator pass. Neither substitutes for the Critic-required executable exits on the specified worktree.

## 7. Hard planning blockers

### 7.1 `CURRENT.md` has not advanced to Round04

At the exact reviewed main commit, `prompts/routes/handoffs/CURRENT.md` still declares:

```text
round_id: round03
route_B critic current prompt: prompts/routes/handoffs/route_B_round03_critic_handoff_20260718.md
allowed Route B tokens: ROUTE_B_ROUND03_...
```

It does not bind the Round04 planning commit, six planning blobs, critic output path, or Round04 token. This conflicts with the repository rule that `CURRENT.md` is the stable current-round entrypoint and the route critic must use the handoff named there.

Required revision: advance `CURRENT.md` to the correct Round04 state or add a current Round04 Route B critic handoff that binds the exact containing main commit, Route B evidence commit, all six blobs, the critic output path, allowed Round04 tokens, and authority boundary. A later planning-file edit must invalidate that handoff.

### 7.2 B10 is unreachable on several authorized terminal branches

The executor plan declares:

```text
B10 depends_on:
  - B6_MYOPS_JOINT_SELECTOR_ABLATION
  - B9_CINE_REGISTERED_TEMPORAL
independent_of_upstream_success: true
```

However, the same contract permits terminal branches before those successful merge receipts exist:

- B1 anatomy repair may return implementation/label revision;
- B2 may return implementation revision or an external-resource blocker;
- B7 may terminate with an official-source blocker or matching defect;
- B8 may produce `CINE_REGISTRATION_BLOCKER`, in which case a fabricated B9 result is forbidden;
- any earlier operational or semantic failure still requires terminal accounting and a reviewable blocker/revision packet.

The first-party wave-preparation helper does not interpret `independent_of_upstream_success` as permission to ignore executor dependencies. It requires every `depends_on` executor to have a successful earlier-wave `MERGED` receipt. Therefore, when B6 or B9 is absent because of an authorized early terminal class, wave 8 cannot prepare B10.

`independent_of_upstream_success` only permits an `afterany` Slurm dependency in the generic plan validator; it does not repair the executor merge DAG.

Required revision: make B10 a controller-level terminal finalizer outside the successful executor merge chain, or set an exact dependency model that permits finalization for every early terminal class. The plan must mechanically show how B10 receives all started attempt IDs and terminal gate receipts when B6 or B9 never produces a merge-ready completion. The revised static validator must test B1 failure, B2 external blocker, B7 blocker, B8 registration blocker, timeout, preemption, cancelled race loser, and successful B6/B9 cases.

### 7.3 B0-B9 do not bind exact validator commands

The Critic request requires every executor to have an exact validator and known-bad contract. The executor plan supplies commands, expected outputs, prose success conditions, and failure branches, but does not bind a `validator` command/path for B0-B9. The controller contract lists semantic failures globally, but it does not state which exact strict command validates each stage, its input directory, output report, expected success token, or expected known-bad failure keys.

The generic `validate_executor_plan.py` cannot close this gap: its required executor field list does not include a validator field. A generic executor-plan PASS therefore proves YAML/task-graph structure, not stage semantic validation.

Required revision: add exact strict validator commands for B0-B10, for example route-local stage validators with fixed input/result paths and required report files. Bind every known-bad fixture to a command, expected nonzero exit, and failure key. The Controller must not decide stage validator implementation or acceptance semantics during execution.

### 7.4 Required native checks have no exit-zero receipt

The current Critic could not run the required commands in `/users/a/e/aereinh/CARE`. The remote Planner audit is useful provenance but is not an independent current-worktree receipt. A ready token cannot be based only on remote/manual inspection when the user explicitly required these executable checks.

Required revision/handoff action: after the planning and DAG fixes, run the exact validator, PyYAML assertions, `git diff --check`, semantic scan, and forbidden-path/interpreter scan on the final bound main commit in the specified `/users` worktree. Record commands, output, and exit `0` in a current Round04 handoff or coordinator receipt before the next independent Critic review.

## 8. Required next action

The Planner/coordinator must:

1. publish a current Round04 entry/handoff in `CURRENT.md`;
2. repair B10 so all early terminal branches can reach deterministic finalization without successful B6/B9 merge receipts;
3. bind exact strict validator commands and known-bad expected failures for every executor;
4. update all affected blobs and rebind the exact main commit;
5. run all mandatory executable checks on `/users/a/e/aereinh/CARE` with exit `0`;
6. request a new independent Round04 Planning Critic review.

The scientific architecture, training budgets, same-split evaluation, Cine fidelity contract, race policy, and authority restrictions should otherwise remain unchanged.

## 9. Authority boundary

This review does not authorize the Route B Controller. It does not authorize implementation, training, Slurm, validation packaging/upload, route promotion, M11, hosted-metric claims, cross-route merge, or a final scientific decision.
