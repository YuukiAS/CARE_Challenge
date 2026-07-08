# M9 Completion Check

status: `M9_NEEDS_MONITOR`

This packet is not `M9_READY_FOR_REVIEW`.

Reason: M9 MyoPS training jobs are running on `htzhulab` and have not completed. A running monitor packet is not completion evidence.

Submitted jobs:

- `58297196` `M9SRRDict` on `a100-gpu`: cancelled after htzhulab mirror started.
- `58297510` `M9SRRDict` on `htzhulab`: running.
- `58297807` `M9SRRDict` lesion/prototype memory isolated run on `htzhulab`: running.
- `58297806` `M9SRRDict` T2 edema focus isolated run on `htzhulab`: running.
- `58297197` `M9CineOut` on `a100-gpu`: cancelled after htzhulab mirror completed.
- `58297511` `M9CineOut` on `htzhulab`: completed, exit code `0:0`, initial output status `M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING`.
- local M9 Cine temporal output rerun: completed locally with status `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`, 12 safe train cases, 12 non-reference frames, and ignored runtime predictions under `runtime_m9_cine_temporal_output/predictions`.

Required before ready review:

- Jobs complete with successful exit code.
- Runtime summaries are aggregated after MyoPS completion.
- All required M9 Markdown/CSV/JSON outputs are populated from current runtime evidence.
- `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py` passes the real packet with `error_count=0`.
- Validator self-test covers all 29 known-bad mutations and fails closed. This part is now satisfied, but the packet remains non-ready until runtime evidence is complete.

No validation package or upload was created. The Cine evidence is local proxy final-output evidence only and does not claim hosted `myocardium_cinemyops` performance.
