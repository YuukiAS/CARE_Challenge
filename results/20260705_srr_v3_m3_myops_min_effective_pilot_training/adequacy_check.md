# Adequacy Check

decision: `PASS`

| requirement | value | status |
| --- | ---: | --- |
| optimizer_steps >= 1200 | 6000 | PASS |
| train_loop_seconds >= 1800 | 2126.2185006489744 | PASS |
| eval_cases >= 12 | 12 | PASS |
| one_batch_overfit | PASS | PASS |
| loss_decrease > 0 | 3.788084328174591 | PASS |
| same_split_help_harm | see `same_split_help_harm.csv` | PASS |

issues: none
