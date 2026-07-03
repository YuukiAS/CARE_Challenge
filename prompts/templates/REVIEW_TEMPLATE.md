---
review_key: "YYYYMMDD_short_slug_review"
task_key: "YYYYMMDD_short_slug"
project: "CARE_Challenge"
reviewer: "separate read-only Codex auditor session or ChatGPT reviewer"
role: "auditor"
read_only: true
audited_status: "TRUE_DONE | PARTIAL_MECHANISM_INCOMPLETE | PREFLIGHT_SMOKE_ONLY | NOT_DONE"
promotion_decision: "GO_FOLD_EXPAND | GO_SUBMISSION_PACKAGE | REVISE | STOP | OPEN_NEXT_TASK | NEEDS_GPT_PLANNER"
---

# CARE Evidence Audit: <task_key>

## Read-Only Boundary
The auditor must not modify code, create missing artifacts, launch training, rerun experiments, package submissions, or upload. If evidence is missing, report it as missing.

## Inputs Reviewed
- Task file:
- Result file:
- MANIFEST:
- Controller report, if any:
- Selection file, if any:
- `metrics_summary` or metric CSV:
- Key logs:
- Key code paths:
- Checkpoint/prediction/export paths:

## Task Goal
Summarize the claimed CARE target metric, mechanism class, and authorized scope.

## Claimed Completion
List executor/controller claims as `claim.<name>: <description>`.

## Claim Ledger
| Claim | Decision (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `CONTRADICTED`) | Evidence | Notes |
| --- | --- | --- | --- |
| claim.example | UNSUPPORTED | evidence not found | Replace with real claim. |

## Supported Claims
List claims fully supported by files, metrics, logs, and CARE gate evidence.

## Partial Claims
List claims with incomplete or proxy evidence.

## Unsupported Claims
List claims lacking evidence.

## Contradicted Claims
List claims contradicted by task boundaries, metrics, logs, label/export checks, no-T2 semantics, or CARE overlay.

## Missing Evidence
Report missing checkpoint, prediction, metric, log, same-split baseline, subgroup metric, HD95, component count, remote FP, volume ratio, cache isolation, label/export QC, or hosted-metric caveat as `evidence not found` or `未找到证据`.

## Permission Boundary Check
State whether the executor stayed within task authorization. Include any unauthorized code change, shell command, commit, push, upload, fold expansion, package build, or training.

## CARE Gate Check
Check the Bridge Kit handoff state, the medical-imaging skill mechanism gate, and `prompts/CARE_OVERLAY_GATES.md`. Note any conflict or overlap explicitly.

## Audited Status
Use exactly one: `TRUE_DONE`, `PARTIAL_MECHANISM_INCOMPLETE`, `PREFLIGHT_SMOKE_ONLY`, or `NOT_DONE`.

## Promotion Decision
Use exactly one: `GO_FOLD_EXPAND`, `GO_SUBMISSION_PACKAGE`, `REVISE`, `STOP`, `OPEN_NEXT_TASK`, or `NEEDS_GPT_PLANNER`.

## Blocked Promotion Reason
If promotion is blocked, explain the missing evidence, boundary issue, failed gate, or need for GPT strategic planning.

## Next Allowed Action
State the next action allowed under the task and CARE overlay. Without `review.md`, `audit.md`, or `controller_report.md`, high-risk/controller work must not proceed to fold expansion, validation packaging, upload, or next-stage training.
