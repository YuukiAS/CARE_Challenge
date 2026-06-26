# Variant Matrix 20260626 Dictionary Bank

Task: `prompts/tasks/20260626_dict_bank.md`

| design | variant | job script | job id | status at submission | result root |
| --- | --- | --- | --- | --- | --- |
| D1 | `multiscale_dictionary` | `jobs/src/run_dict_bank_multiscale.sh` | `56611484` | `PD` on `htzhulab`, reason `Resources` | `results/20260626_dict_bank/variants/multiscale_dictionary/` |
| D2 | `task_specific_dictionary` | `jobs/src/run_dict_bank_task_specific.sh` | `56611485` | `PD` on `htzhulab`, reason `Priority` | `results/20260626_dict_bank/variants/task_specific_dictionary/` |
| D4 | `cross_modal_interaction_dictionary` | `jobs/src/run_dict_bank_interaction.sh` | `56611486` | `PD` on `htzhulab`, reason `Priority` | `results/20260626_dict_bank/variants/cross_modal_interaction_dictionary/` |
| D5 | `anchor_guided_dictionary` | `jobs/src/run_dict_bank_anchor.sh` | `56611487` | `PD` on `htzhulab`, reason `Priority` | `results/20260626_dict_bank/variants/anchor_guided_dictionary/` |
| D6 | `hierarchical_router_dictionary` | `jobs/src/run_dict_bank_hierarchical.sh` | `56611488` | `PD` on `htzhulab`, reason `Priority` | `results/20260626_dict_bank/variants/hierarchical_router_dictionary/` |

## Preflight Gate

All five variants completed one-step CPU forward/backward gates with `--skip-export` under `results/20260626_dict_bank/preflight/variants/`.

The preflight gate proves interface compatibility only. It is not a metric result and must not be used for model selection.
