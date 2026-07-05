# MANIFEST: 20260704 SRR-v2.5 Failure Analysis Overlay

task: `prompts/tasks/20260704_srr_v25_failure_analysis_overlay.md`
result: `results/20260704_srr_v25_failure_analysis_overlay/result.md`
review: `results/20260704_srr_v25_failure_analysis_overlay/review.md` (not created)

## Artifacts

| path | purpose |
| --- | --- |
| `result.md` | Executor summary and gate decision. |
| `case_error_taxonomy.csv` | Hard-subgroup taxonomy comparing SRR argmax and pathology-aware outputs. |
| `overlay_manifest.md` | Overlay case/slice/panel manifest and evidence limitations. |
| `overlays/Case1002_myops_scar_failure_overlay.png` | No-T2 scar overlay. |
| `overlays/Case2002_myops_scar_failure_overlay.png` | T2-present scar overlay. |
| `overlays/Case2002_myops_edema_failure_overlay.png` | T2-present edema overlay. |
| `overlays/Case3004_myops_scar_failure_overlay.png` | CenterC scar overlay. |
| `overlays/Case3004_myops_edema_failure_overlay.png` | CenterC edema overlay. |
| `overlays/Case3011_myops_scar_failure_overlay.png` | CenterC scar overlay. |
| `overlays/Case3011_myops_edema_failure_overlay.png` | CenterC edema overlay. |
| `proposal_vs_refiner_breakdown.csv` | Proposal metrics versus final decode/refiner outcomes. |
| `dictionary_gate_trace.csv` | Aggregated retrieval usage trace from training step logs. |
| `nnunet_context_trace.csv` | Same-split nnU-Net case metrics for context. |
| `residual_gate_trace.csv` | Baseline residual/gate and crop residual trace. |
| `hard_case_summary.md` | Human-readable harm localization summary. |
| `pre_training_decision.md` | Pre-training gate decision and next required evidence. |
| `hard_subgroup_runtime/` | 1-step tiny CPU runtime used only to export explicit hard-subgroup predictions. |
| `hard_subgroup_overlay/` | Raw generated hard-subgroup overlay packet before copying key artifacts to top level. |
| `hard_subgroup_help_harm/` | Same-split nnU-Net help/harm comparison for the hard-subgroup smoke packet. |
| `bounded_matrix_overlay/` | Per-variant overlays and traces for the six non-identity bounded matrix rows. |
| `bounded_matrix_overlay/bounded_matrix_overlay_summary.md` | Matrix-level taxonomy count summary and interpretation. |
| `bounded_matrix_overlay/bounded_matrix_overlay_taxonomy.csv` | Aggregated taxonomy rows for six bounded matrix variants. |
| `bounded_matrix_overlay/bounded_matrix_overlay_proposal_refiner.csv` | Aggregated proposal/refiner linkage for six bounded matrix variants. |
| `bounded_matrix_overlay/bounded_matrix_overlay_dictionary_trace.csv` | Aggregated retrieval trace rows for six bounded matrix variants. |
| `bounded_matrix_overlay/bounded_matrix_overlay_residual_gate_trace.csv` | Aggregated residual gate trace rows for six bounded matrix variants. |

## Status

`EXECUTED_UNAUDITED`; hard-subgroup overlays, same-split help/harm context, and
six non-identity bounded matrix overlay/taxonomy packets now exist for
`Case1002`, `Case2002`, `Case3004`, and `Case3011`. Anchor-enabled rows do not
show remote-FP flooding in this packet, while `srr_v25_no_anchor` does. Full
fold0 subgroup metrics, spatial proposal/dictionary maps if needed, and
read-only audit remain missing.
