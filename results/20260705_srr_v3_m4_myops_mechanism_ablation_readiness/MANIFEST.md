# MANIFEST

task: `prompts/tasks/20260705_srr_v3_m4_myops_mechanism_ablation_readiness.md`
result_dir: `/users/a/e/aereinh/CARE/results/20260705_srr_v3_m4_myops_mechanism_ablation_readiness`

| artifact | purpose |
| --- | --- |
| `result.md` | executor summary |
| `ablation_matrix_contract.md` | M4 matrix scope and provenance |
| `ablation_config_table.csv` | run/not-run ablation rows |
| `same_split_help_harm.csv` | same-split nnU-Net comparison by case/class |
| `gate_residual_by_ablation.csv` | gate/residual/decode-delta stats |
| `prototype_dictionary_by_ablation.csv` | prototype and dictionary diagnostics |
| `proposal_refinement_by_ablation.csv` | proposal/refinement metrics |
| `mechanism_decision.md` | bounded attribution conclusion |
| `completion_check.md` | executor readiness check |
| `review_request.md` | independent review request |
| `MANIFEST.md` | artifact index |
| `commands_run.md` | command provenance |
| `slurm_status.md` | Slurm job status and exit-code evidence without committing logs |

No checkpoints, NIfTI predictions, validation packages, uploads, or logs are included in the lightweight committed packet.
