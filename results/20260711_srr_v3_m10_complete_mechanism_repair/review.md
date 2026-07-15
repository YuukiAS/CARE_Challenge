# M10 Independent Runtime Review

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Reviewer role: independent read-only CARE Codex reviewer.

Decision: `M10_AUDITED_NEEDS_REVISION`

This is not an audited-go review. The submitted controller packet is terminal
enough to review as a fail-closed packet, but it does not satisfy the M10
contract for completion or route decision.

## Contract Sources Reviewed

- `AGENTS.md`
- `prompts/shared/REVIEWER_PROMPTS.md`, section `M10 reviewer: SRR-v3 complete mechanism repair`
- `prompts/shared/EXECUTOR_PROMPTS.md`, section `M10 executor/controller: SRR-v3 complete mechanism repair`
- `results/20260711_srr_v3_m10_complete_mechanism_repair/`

## Evidence Reviewed

- `completion_check.md`
- `controller_report.md`
- `result.md`
- `review_request.md`
- `validator_report.md`
- `finalizer_state.json`
- `wave3_cine_terminal_finalization.json`
- `MANIFEST.md`
- Live Slurm terminal accounting via `sacct` for M10 Wave 2 and Wave 3 jobs.

## Findings

1. Canonical M10 contract hash drift violates the prerequisite gate.

   The packet records planning review hash
   `5030af7d74e35a423dd7e782ed0d55dffc1c1e78335c4016bb75920c17da0e64`,
   while the current canonical M10 prompt hash is
   `955f6ab31e523123ba339e5b1732b78b304f099b9ce92bc896dfbb1e5d76653f`.
   The packet attributes this drift to commit `c53fa06` changing M10 Slurm
   continuity/finalizer terms. The M10 contract treats this as
   `M10_BLOCKED_PREREQUISITE`; a reviewer cannot self-reconcile the planning
   hash or convert this packet to audited completion.

2. Wave 3 registration failed its contract gate and blocked learned temporal
   training.

   The terminal Wave 3 evidence records:

   | Phase | Job | State | Review interpretation |
   | --- | ---: | --- | --- |
   | CineMA adapter | `58848099` | `COMPLETED 0:0` | terminal adapter evidence exists |
   | learned Cine registration | `58848203` | `FAILED 2:0` | adequate run, but registration gate failed |
   | learned temporal dictionary | `58848205` | `CANCELLED 0:0` | dependency-cancelled; zero temporal training credit |
   | Wave 3 finalizer | `58848313` | `COMPLETED 0:0` | terminal accounting collected |

   The registration gate failed because
   `case_non_worse_rate=0.8888888888888888` is below the required `0.90`.
   Under the M10 contract, this blocks learned temporal training; frame0
   fallback is not an acceptable completion substitute.

3. Live Slurm accounting supports terminal state, not monitor state.

   I independently checked `sacct` for the relevant M10 jobs. Wave 2 retry11
   jobs `58706293`, `58775065`, `58775066`, `58775067`, `58775068`,
   `58775069`, and `58775070` are terminal `COMPLETED 0:0`. Wave 3 jobs are
   terminal as listed above. Therefore this review is not returning
   `NEEDS_MONITOR`; the blocker is unmet contract/evidence, not pending Slurm
   accounting.

4. The packet itself does not request normal M10 audited completion.

   `review_request.md`, `completion_check.md`, `result.md`, and
   `finalizer_state.json` all label the packet as prerequisite-blocked or
   fail-closed. The packet explicitly says not to perform normal M10
   scientific review from it and not to start M11.

## Controlled Decision

`M10_AUDITED_NEEDS_REVISION`

Rationale: the current M10 packet has terminal accounting, but the canonical
contract hash prerequisite is mismatched and the Wave 3 registration gate
failed, which legally blocks learned temporal completion. No route promotion,
route-negative scientific conclusion, validation packaging/upload, hosted
metric claim, M11 start, or audited-go is authorized from this packet.
