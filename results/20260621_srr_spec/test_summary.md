# Test Summary 20260621 SRR Spec

status: `pass`

## Commands

| command | result |
| --- | --- |
| `./envs/env_CARE/bin/python -m py_compile src/care_myocardium/data/case_metadata.py src/care_myocardium/data/myops_dataset.py src/care_myocardium/models/srr_blocks.py src/care_myocardium/models/pathology_heads.py src/care_myocardium/models/srr_myops.py src/care_myocardium/losses/srr_losses.py scripts/training/run_srr_myops.py scripts/evaluation/report_srr_myops.py` | exit `0` |
| `bash -n jobs/src/run_srr_myops_fold0.sh` | exit `0` |
| `./envs/env_CARE/bin/python -m unittest discover -s src/care_myocardium/tests -p 'test_srr_*.py'` | `Ran 7 tests`, `OK` |
| `./envs/env_CARE/bin/python scripts/training/run_srr_myops.py --smoke --output-json results/20260621_srr_spec/one_batch_smoke.json` | exit `0`, smoke JSON written |
| `./envs/env_CARE/bin/python scripts/evaluation/report_srr_myops.py --smoke-json results/20260621_srr_spec/one_batch_smoke.json --output-md results/20260621_srr_spec/smoke_report.md` | exit `0` |

## Required Checks

| check | evidence | result |
| --- | --- | --- |
| Three real modality combinations forward | `test_srr_shapes.py` uses complete, `C0+LGE`, and `LGE-only` availability vectors | pass |
| Missing modality masking | `test_srr_missingness.py` changes absent T2 from zero to `1e6`; max output difference `<1e-5` | pass |
| T2-present edema gradient | `test_srr_losses.py` verifies nonzero `edema_logits` gradient | pass |
| No-T2 edema dense loss | `test_srr_losses.py` verifies component loss and gradient are exactly zero when T2 is absent | pass |
| LGE-only scar gradient | `test_srr_losses.py` verifies scar head gradient with `LGE-only` availability | pass |
| Gate normalization / no NaN | `test_srr_shapes.py` and smoke JSON gate sums are all `1.0` | pass |
| Expert coverage metrics | `one_batch_smoke.json` records entropy and coverage metrics for anatomy/scar/edema gates | pass |
| Compact label mapping | `test_srr_losses.py` verifies `4->1220`, `5->2221` | pass |

## One-Batch Smoke

- output: `results/20260621_srr_spec/one_batch_smoke.json`
- status: `pass`
- logits shape: `[3, 6, 8, 12, 10]`
- loss: `3.4006993770599365`
- validation upload: not run
