# MyoPS-Net fold0 modality-group metrics

| modality group | n cases | myops_edema class_4 | myops_scar class_5 | foreground_mean |
| --- | ---: | ---: | ---: | ---: |
| C0+LGE | 4 | NA | 0.3778 | 0.3778 |
| C0+LGE+T2 | 16 | 0.3944 | 0.6933 | 0.5439 |
| LGE | 24 | NA | 0.5018 | 0.5018 |

Notes:
- class_4 is CARE `myops_edema`; class_5 is CARE `myops_scar`.
- `NA` means every case in that group was GT-empty for that class and had no false-positive prediction in the evaluator output.
