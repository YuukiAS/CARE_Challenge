# SRR Rescue Ablation Result

Task: `prompts/tasks/20260625_srr_rescue_ablate.md`

## Outcome

- Model selection: `SELECT_SRR_RECOVERED`.
- Selected fold0 route: `best_srr_recovered` / `srr_expert_dropout` from Phase 1.
- New Phase 2 jobs completed successfully on `htzhulab`: `56469952` late fusion and `56469990` weak SIP retrieval.

## Key Files

- `model_selection.md`
- `metrics_summary.md`
- `ablation_matrix.csv`
- `subgroup_metrics.csv`
- `retrieval_diagnostics.csv`
- `efficiency.csv`

## Caveats

- This is fold0 evidence only.
- Absolute scar/edema scores remain low; the selection is relative among tested ablations.
- No validation submission, upload package, external data, or folds1-4 expansion was performed.
