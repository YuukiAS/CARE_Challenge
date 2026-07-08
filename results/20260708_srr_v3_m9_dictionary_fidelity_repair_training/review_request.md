# M9 Review Request

status: `DO_NOT_REVIEW_AS_READY_NEEDS_MONITOR`

This is not a normal review-ready request. It records current executor progress and pending Slurm job IDs only.

Do not issue `M9_AUDITED_REPAIR_CONTRACT_READY` or any ready/audited-go decision from this monitor packet. The next executor step is to wait for running jobs `58297510`, `58297807`, and `58297806`, rerun aggregation after additional runtime summaries are written, replace pending runtime rows with evidence, rerun strict validation, then write a final review request if evidence supports it.

Cine local proxy final-output evidence has been added after the initial Cine job: `m9_cine_final_output_manifest.csv` now records 12 safe train cases and 12 non-reference frames with ignored runtime predictions under `runtime_m9_cine_temporal_output/predictions`. This does not claim hosted `myocardium_cinemyops` performance or route readiness.

Partial MyoPS runtime aggregation is present for three formal outputs:

- `m9_srr_main_true_br2_pattern_sip`: `6000` optimizer steps, `20` validation events, `1660.097` train-loop seconds, and negative mean Dice deltas vs the tracked M8 nnU-Net anchor (`myops_scar=-0.009682347345035466`, `myops_edema=-0.076883272409283`).
- `m9_srr_main_lesion_proposal_memory`: `6000` optimizer steps, `1499.562` train-loop seconds, and negative mean Dice deltas vs the tracked M8 nnU-Net anchor (`myops_scar=-0.03627368193360481`, `myops_edema=-0.07598376935449123`).
- `m9_srr_main_t2_edema_recall_focus`: `6000` optimizer steps, `20` validation events, `1655.343` train-loop seconds, and negative mean Dice deltas vs the tracked M8 nnU-Net anchor (`myops_scar=-0.06778769437264179`, `myops_edema=-0.08746046393754325`).

This is monitor evidence, not a review-ready completion packet. The aggregate formal train-loop seconds are still only `4815.002`, all three MyoPS jobs are still running, and none of the aggregated formal candidates beats the tracked M8 nnU-Net anchor.
