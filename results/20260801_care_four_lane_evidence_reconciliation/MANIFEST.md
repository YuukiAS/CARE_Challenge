# Manifest

task: `prompts/tasks/20260801_care_four_lane_evidence_reconciliation_controller.md`
result: `results/20260801_care_four_lane_evidence_reconciliation/result.md`
review: not required by task frontmatter

## Core Evidence

| path | purpose |
| --- | --- |
| `controller_context.json` | controller bootstrap, visual-reading source note, fixed permissions, selected steps |
| `frozen_asset_manifest.json` | SHA256 manifest for selected checkpoints, split receipt, and evaluation scripts |
| `metric_contract.json` | corrected metric semantics and physical-unit thresholds |
| `all_outer_casewise.csv` | all stock/M0R/M2 outer casewise metrics |
| `all_outer_summary.csv` | denominator-separated stock/M0R/M2 outer summaries |
| `m0r_vs_stock_outer_casewise.csv` | same-case M0R minus stock comparison |
| `m0r_vs_stock_outer_summary.csv` | M0R same-case summary and harm fraction |
| `m2_outer_casewise.csv` | M2 outer casewise comparison against stock |
| `m2_vs_stock_outer_summary.csv` | M2 candidate gate summary |
| `sentinel_case_comparison.csv` | required sentinel cases |
| `inner_stock_privilege_audit.csv` | proof that M0R inner selection cases were seen by fold-specific stock training |
| `m1_fidelity_audit.json` | M1 implementation-fidelity classification |
| `m3_fidelity_audit.json` | M3 implementation-fidelity classification |
| `four_lane_scientific_interpretation.md` | human-readable scientific conclusion |
| `scientific_decision.json` | machine-readable allowed scientific decision |
| `evaluation_receipt.json` | frozen replay receipt |
| `strict_validator_report.json` | strict validator output |
| `known_bad_report.json` | known-bad rejection matrix |
| `controller_report.md` | terminal controller report |
| `completion_check.md` | terminal completion check |
| `notification_brief.json` | notifier input, written after push accounting |

## Source Changes

| path | purpose |
| --- | --- |
| `scripts/evaluation/four_lane_reconciliation/evaluate_frozen_outer.py` | first-party frozen evaluator with physical-space metrics |
| `scripts/validation/validate_four_lane_evidence_reconciliation.py` | fail-closed packet validator |
| `tests/four_lane_reconciliation/test_metric_contract.py` | regression tests for physical HD and physical-volume small-lesion semantics |
| `prompts/routes/handoffs/CURRENT.md` | current state updated to corrected no-candidate result |
| `wiki/README.md` | root wiki updated to corrected no-candidate result |

No checkpoint, NIfTI prediction, raw data, upload package, or large runtime log is tracked in this packet.
