# M9 Completion Check

status: `M9_NEEDS_MONITOR`

This packet is not `M9_READY_FOR_REVIEW`.

Reason: M9 isolated MyoPS training jobs are running on `htzhulab` and have not completed. A running monitor packet is not completion evidence.

Partial aggregation evidence:

- `m9_srr_main_true_br2_pattern_sip` has runtime formal outputs aggregated.
  - optimizer steps: `6000`
  - validation events: `20`
  - train loop seconds: `1660.097`
  - mean Dice delta vs tracked M8 nnU-Net anchor control: `myops_scar=-0.009682347345035466`, `myops_edema=-0.076883272409283`
- `m9_srr_main_lesion_proposal_memory` has runtime formal outputs aggregated from `runtime_htzhulab_mirror`.
  - optimizer steps: `6000`
  - train loop seconds: `1499.562`
  - mean Dice delta vs tracked M8 nnU-Net anchor control: `myops_scar=-0.03627368193360481`, `myops_edema=-0.07598376935449123`
- `m9_srr_main_t2_edema_recall_focus` has runtime formal outputs aggregated from `runtime_htzhulab_mirror`.
  - optimizer steps: `6000`
  - validation events: `20`
  - train loop seconds: `1655.343`
  - mean Dice delta vs tracked M8 nnU-Net anchor control: `myops_scar=-0.06778769437264179`, `myops_edema=-0.08746046393754325`
- Current aggregated formal training budget rows: `3`.
- Current aggregate train-loop seconds: `4815.002`, below the M9 threshold of `28800` seconds and below the alternative gate of three formal SRR-main candidates with `>=7200` seconds each plus one control eval.
- interpretation: `SCIENTIFIC_UNDERTRAINED_OR_NEGATIVE_PARTIAL_EVIDENCE`; not ready, not promotion.

Submitted jobs:

- `58297196` `M9SRRDict` on `a100-gpu`: cancelled after htzhulab mirror started.
- `58297510` `M9SRRDict` on `htzhulab`: completed with exit code `0:0`.
- `58297807` `M9SRRDict` lesion/prototype memory isolated run on `htzhulab`: running.
- `58297806` `M9SRRDict` T2 edema focus isolated run on `htzhulab`: running.
- `58297197` `M9CineOut` on `a100-gpu`: cancelled after htzhulab mirror completed.
- `58297511` `M9CineOut` on `htzhulab`: completed, exit code `0:0`, initial output status `M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING`.
- local M9 Cine temporal output rerun: completed locally with status `FOUND_LOCAL_TEMPORAL_FINAL_OUTPUTS`, 12 safe train cases, 12 non-reference frames, and ignored runtime predictions under `runtime_m9_cine_temporal_output/predictions`.

Required before ready review:

- Remaining jobs complete with successful exit code.
- Runtime summaries are aggregated again after MyoPS jobs reach terminal states.
- All required M9 Markdown/CSV/JSON outputs are populated from current runtime evidence.
- `scripts/evaluation/validate_srr_v3_m9_dictionary_fidelity_packet.py` passes the real packet with `error_count=0`.
- Validator self-test covers all 29 known-bad mutations and fails closed. This part is now satisfied, but the packet remains non-ready until runtime evidence is complete.

No validation package or upload was created. The Cine evidence is local proxy final-output evidence only and does not claim hosted `myocardium_cinemyops` performance.
