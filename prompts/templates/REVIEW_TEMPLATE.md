---
task_key: "YYYYMMDD_short_slug"
reviewed_commit: "<git commit containing the packet under review>"
reviewed_packet_manifest_sha256: "<sha256 of results/<task_key>/MANIFEST.md>"
review_decision: "NEEDS_EVIDENCE | NEEDS_MONITOR | NEEDS_REVISION | AUDITED_GO"
review_token: "<controlled token for this task>"
route_promotion_decision: "NOT_REVIEWED | PROMOTE_ROUTE | NO_PROMOTION | NEEDS_GPT_PLANNER"
route_negative_decision: "NOT_REVIEWED | STOP_SUPPORTED | STOP_NOT_SUPPORTED | NOT_EVALUABLE"
scientific_resolution_status: "AWAITING_REVIEW | SCIENTIFIC_PROMOTED | SCIENTIFIC_STOP_SUPPORTED | SCIENTIFIC_UNRESOLVED | SCIENTIFIC_UNDERTRAINED | SCIENTIFIC_PIPELINE_BUG | SCIENTIFIC_NEEDS_EVIDENCE | SCIENTIFIC_NEEDS_REVISION"
reviewed_at: "<UTC timestamp>"
role: "reviewer"
read_only: true
---

# CARE Runtime Review: <task_key>

## Read-Only Boundary

The reviewer is independent and read-only. Do not fix code, generate missing
artifacts, resume monitors, submit jobs, package/upload validation, push, or
start another milestone. If evidence is missing, report it as missing.

## Inputs Reviewed

- Task or milestone staging file:
- Result packet directory:
- `MANIFEST.md`:
- `controller_report.md`, if any:
- `completion_check.md`:
- `review_request.md`:
- Key lightweight evidence files:

## Packet Identity

Record `reviewed_commit`, `reviewed_packet_manifest_sha256`, and the exact
packet path. The reviewed packet must already be committed before this review.

## Claim Ledger

| Claim | Decision (`SUPPORTED`, `PARTIAL`, `UNSUPPORTED`, `CONTRADICTED`) | Evidence | Notes |
| --- | --- | --- | --- |
| claim.example | UNSUPPORTED | evidence not found | Replace with real claim. |

## Completion And Monitor Gate

Reject any packet that treats a monitor packet, pending Slurm state, submitted
job, running job, or awaiting accounting state as completion. `commands_run.md`
showing only submission or pending status is not completion evidence.

## Permission Boundary Check

State whether executor/controller/finalizer stayed within task authorization,
including code changes, shell commands, commits, uploads, package builds,
training, and push boundaries.

## Evidence Adequacy

For model or scientific work, audit the exact task-required evidence and mark
claims `PARTIAL`, `UNSUPPORTED`, or `CONTRADICTED` when evidence is absent,
undertrained, stale, synthetic-only, cache-contaminated, mislabeled, or outside
the authorized scope.

## Decisions

Use the frontmatter fields above. Reviewer may support or reject claims, decide
whether a next planning round is allowed, or request evidence/revision/monitor.
Reviewer must not directly authorize fold expansion, validation packaging,
upload, push, or a new milestone execution.
