# M10 Terminal Failure Packet Review Boundary

This packet does not request M10 scientific review yet. It records an original prerequisite stop, a later prerequisite repair, wave 1 acceptance, original wave 2 Slurm terminal failure, and an authorized replacement Wave 2 enhanced compute-node preflight now in `NEEDS_MONITOR`.

The wave 2 executor submitted seven serial `htzhulab` jobs. Formal monitor at `2026-07-11T15:45:38Z` found all seven jobs terminal `FAILED` with exit code `1:0`. Logs show the shared failure cause is missing `mpmath` for `sympy` during PyTorch optimizer initialization.

Fail-closed aggregation wrote lightweight phase packets with `STARTUP_FAILED_NEEDS_EVIDENCE`. Because these are startup failures without valid runtime summaries, checkpoint selections, full-case metrics, or causal intervention evidence, this packet is not ready for normal independent review.

Blocked actions until terminal post-job aggregation exists:

- write `review.md`
- launch wave 3
- package or upload validation
- claim hosted metrics
- claim route promotion or scientific stop
- start M11

The next action is to wait for active enhanced preflight job `58683497` terminal accounting. Only if it exits `0` may the controller submit the formal replacement Wave 2 jobs with training-to-training `afterok` dependencies. Prior preflight job `58682781` was superseded before formal submission and is not a formal gate. No replacement Slurm training jobs were submitted by this packet.
