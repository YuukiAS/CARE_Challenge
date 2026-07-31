# Completion check

| gate | status | evidence |
|---|---|---|
| Task prompt read fully | PASS | `prompts/tasks/20260731_care_metric_truth_reconciliation.md` |
| Parallel overview read | PASS | `prompts/tasks/20260731_care_parallel_next_steps.md` |
| Main-only isolated branch/worktree | PASS | branch `task/20260731-metric-truth`, worktree `/users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731` |
| D0-D3 traced to implementation and manifests | PASS | `decoder_reset_score_semantics.json`, `decoder_reset_score_lineage.csv` |
| Clean OOF / inner-select / outer-once / full-data / hosted split | PASS | `metric_semantics_contract.json`, `metric_truth_table.csv` |
| Scar / official pure edema / internal edema-zone split | PASS | `metric_semantics_contract.json` |
| Canonical T2-present denominator reverified | PASS | `80` rows in `/users/a/e/aereinh/CARE/results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_t2_present_case_manifest.csv` |
| Hosted MoSAIC reference binding | PASS | leaderboard row + user attestation + source commit + downloaded weight SHA256s + recipe binding; exact ZIP unavailable and recorded as boundary |
| metric_contract_status | PASS | `metric_truth_receipt.json` |
| New training / upload / checkpoint tuning | PASS | none performed |
| New Slurm job in this task | PASS | none used |
| Strict validator | PASS | `strict_validator_report.json`, command: `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/forensics/metric_truth/validate_metric_truth.py --result-dir results/20260731_care_metric_truth_reconciliation --report-json results/20260731_care_metric_truth_reconciliation/strict_validator_report.json` |
| Known-bad tests | PASS | 15 passed with `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python -m pytest tests/forensics/metric_truth/test_metric_truth_known_bad.py -q` |
| Local commit | PENDING_COMMIT | validator passed; commit to be created after final file update |
| Push | NOT_AUTHORIZED | no push will be performed |

| Late user Deep Research draft source | PASS | Read only, source SHA `41ab0c185f0fb26398bbcfcec2b0134d51ffdb478d4cf66b8a5334b49dd749ac`; not moved under current write scope |
