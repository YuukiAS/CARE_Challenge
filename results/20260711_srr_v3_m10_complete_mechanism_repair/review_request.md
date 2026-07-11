# M10 Terminal Failure Packet Review Boundary

This packet does not request M10 scientific review yet. It records an original prerequisite stop, a later prerequisite repair, wave 1 acceptance, and wave 2 Slurm terminal failure now in `NEEDS_EVIDENCE`.

The wave 2 executor submitted seven serial `htzhulab` jobs. Formal monitor at `2026-07-11T15:45:38Z` found all seven jobs terminal `FAILED` with exit code `1:0`. Logs show the shared failure cause is missing `mpmath` for `sympy` during PyTorch optimizer initialization.

Fail-closed aggregation wrote lightweight phase packets with `STARTUP_FAILED_NEEDS_EVIDENCE`. Because these are startup failures without valid runtime summaries, checkpoint selections, full-case metrics, or causal intervention evidence, this packet is not ready for normal independent review.

Blocked actions until terminal post-job aggregation exists:

- write `review.md`
- launch wave 3
- package or upload validation
- claim hosted metrics
- claim route promotion or scientific stop
- start M11

The next action requires explicit authorization for another execution attempt. The project-local dependency has been repaired to `mpmath 1.3.0`, but no replacement Slurm training jobs were submitted by this controller packet.
