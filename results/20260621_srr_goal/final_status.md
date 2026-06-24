# Final Status 20260621 SRR Goal

status: `MYOPS_REVISE_SRR`

## Subtask Status

| subtask | path | status |
| --- | --- | --- |
| SRR spec | `results/20260621_srr_spec/result.md` | `GO_FOLD0` |
| SRR fold0 | `results/20260621_srr_fold0/result.md` | `REVISE_ROUTING` |
| SRR ablation | `prompts/tasks/20260621_srr_ablation.md` | not started; fold0 did not reach `GO_ABLATION` |
| SRR expand | `prompts/tasks/20260621_srr_expand.md` | not started |
| Cine retrieval | `/overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval/results/20260621_cine_retrieval/result.md` | `REVISE_GEOMETRY`, no training jobs |

## MyoPS Fold0 Jobs

| job | variant | state | elapsed | stop reason | log |
| --- | --- | --- | --- | --- | --- |
| `55720659` | `conditional_dualhead_control` | `COMPLETED` | `00:12:20` | short wiring run | `logs/SRRCondF0_55720659_20260621_191600.log` |
| `55720658` | `srr_minimal` | `COMPLETED` | `00:19:09` | short wiring run | `logs/SRRMinF0_55720658_20260621_191600.log` |
| `55723114` | `conditional_dualhead_control` | `COMPLETED` | `04:06:08` | `max_steps` | `logs/SRRCondF0_55723114_20260621_193914.log` |
| `55723115` | `srr_minimal` | `COMPLETED` | `04:31:04` | `max_runtime_seconds` | `logs/SRRMinF0_55723115_20260621_193914.log` |

GPU allocation for corrected jobs: `gres/gpu:nvidia_h100_nvl=1` on `htzhulab`.

## Selected MyoPS Config

No model is selected for ablation, fold expansion, or validation. The current local candidate `srr_minimal` produced positive fold0 signal but requires routing revision before any next task.

## Fold0 Metrics

| variant | class | group | n | Dice | HD | HD95 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `conditional_dualhead_control` | `myops_edema` | all cases | 44 | 0.2901 | 104.8699 | 81.8594 |
| `conditional_dualhead_control` | `myops_edema` | GT-positive | 16 | 0.1103 | 176.9680 | 138.1377 |
| `conditional_dualhead_control` | `myops_scar` | all cases | 44 | 0.0581 | 169.7511 | 113.4492 |
| `srr_minimal` | `myops_edema` | all cases | 44 | 0.5973 | 69.9282 | 49.0718 |
| `srr_minimal` | `myops_edema` | GT-positive | 16 | 0.1426 | 174.8206 | 122.6796 |
| `srr_minimal` | `myops_scar` | all cases | 44 | 0.0832 | 168.3660 | 120.8677 |

No 5-fold SRR metrics exist; folds 1-4 were not started.

## Retrieval Diagnostics

`results/20260621_srr_fold0/retrieval_usage.md`:

- anatomy: per-expert means `expert0=0.5130`, `expert1=0.0012`, `expert2=0.0004`, `expert3=0.4854`; max row `1.0000`
- scar: per-expert means `expert0=0.0006`, `expert1=0.9431`, `expert2=0.0558`, `expert3=0.0005`; max row `1.0000`
- edema: per-expert means `expert0=0.4126`, `expert1=0.2996`, `expert2=0.2864`, `expert3=0.0015`; max row `1.0000`

Gate: `REVISE_ROUTING`.

## Cine Result

The Cine secondary line did not train. It stopped at `REVISE_GEOMETRY` because frame0/reference evidence was plausible but strict metadata match was only `59/64`, with 4 origin mismatches and 1 spacing mismatch, and geometry-aware crop/inverse mapping was not proven.

## Not Executed

- no `20260621_srr_ablation`
- no `20260621_srr_expand`
- no folds 1-4
- no validation submission
- no upload-ready package
- no external upload
- no network
- no external data or external weights

## Next Task Recommendation

Open a narrow SRR routing revision task before ablation. The next task should target router anti-collapse/entropy/coverage behavior and keep the same fold0 evaluator/cache discipline. Cine should remain blocked until a geometry-revision task proves reference-frame metadata and inverse mapping safety.
