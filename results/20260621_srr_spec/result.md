# Result 20260621 SRR Spec

status: `GO_FOLD0`

## Execution Summary

Completed the Result4 SRR specification task. `Result4.pdf` was extracted to `results/20260621_srr_spec/Result4.txt`, the SRR architecture contract was frozen, and a minimal first-party SRR-MyoPS-Lite skeleton plus unit tests and one-batch smoke entrypoint were added.

No network, external upload, validation submission, validation package, external data, external weights, or third-party baseline patching was performed.

## Result4 Method Story

Adopted Result4 as a segmentation-native selective representation retrieval method, not as a literal copy of the original R2/BR2 linear learner. The frozen first pass is:

- modality-specific LGE/T2/C0 stems;
- shared/private representation retrieval blocks;
- router input from availability vector plus masked feature summary;
- strict invalid-modality masking before fusion and inside expert routing;
- anatomy/scar/edema target-specific routes and heads;
- T2-masked edema dense supervision;
- LGE-preserving scar fallback for LGE-only cases;
- soft anatomy containment prior;
- SIP-inspired entropy plus coverage/load-balancing regularization;
- no center-ID dependency at inference;
- optional alignment disabled until a later ablation proves it is necessary.

## Adopted And Deleted Modules

Adopted:

- SRR-MyoPS-Lite first-party skeleton under `src/care_myocardium/`.
- T2-conditioned edema loss and strict no-T2 dense loss masking.
- Shared/private gated feature retrieval with disabled unavailable private experts.
- Soft anatomy prior, not hard ROI deletion.

Deleted/postponed from the first pass:

- original R2/BR2 discrete SIP/support optimization;
- center-ID source routing;
- feature/image alignment expert;
- interaction dictionaries and temporal unification;
- validation packaging and fold expansion.

## Code Paths

- `src/care_myocardium/data/case_metadata.py`
- `src/care_myocardium/data/myops_dataset.py`
- `src/care_myocardium/models/srr_blocks.py`
- `src/care_myocardium/models/pathology_heads.py`
- `src/care_myocardium/models/srr_myops.py`
- `src/care_myocardium/losses/srr_losses.py`
- `src/care_myocardium/configs/srr_myops_minimal.yaml`
- `src/care_myocardium/tests/test_srr_shapes.py`
- `src/care_myocardium/tests/test_srr_missingness.py`
- `src/care_myocardium/tests/test_srr_losses.py`
- `scripts/training/run_srr_myops.py`
- `scripts/evaluation/report_srr_myops.py`
- `jobs/src/run_srr_myops_fold0.sh`

## Commands And Results

| command | result |
| --- | --- |
| `pdftotext docs/notes/deep_research/Result4.pdf results/20260621_srr_spec/Result4.txt` | exit `0`, `780` lines |
| `./envs/env_CARE/bin/python -m py_compile ...` | exit `0` |
| `bash -n jobs/src/run_srr_myops_fold0.sh` | exit `0` |
| `./envs/env_CARE/bin/python -m unittest discover -s src/care_myocardium/tests -p 'test_srr_*.py'` | `Ran 7 tests`, `OK` |
| `./envs/env_CARE/bin/python scripts/training/run_srr_myops.py --smoke --output-json results/20260621_srr_spec/one_batch_smoke.json` | exit `0` |
| `./envs/env_CARE/bin/python scripts/evaluation/report_srr_myops.py --smoke-json results/20260621_srr_spec/one_batch_smoke.json --output-md results/20260621_srr_spec/smoke_report.md` | exit `0` |

## Test Evidence

See `results/20260621_srr_spec/test_summary.md`.

Required checks passed:

- real modality combinations forward;
- absent modality extreme-value invariance;
- T2-present edema nonzero gradient;
- no-T2 edema dense loss and gradient zero;
- LGE-only scar gradient;
- normalized finite gates;
- expert usage/coverage metrics;
- compact label `4/5` mapping.

## Git Diff Summary

The current additions are untracked task artifacts and first-party skeleton files. `git diff --stat` is empty because these files are new and not staged. `git status --short` shows new task-scoped paths under `results/20260621_srr_spec/`, `results/20260621_srr_goal/`, `src/care_myocardium/`, `scripts/`, and `jobs/src/`.

## Artifacts

Manifest: `results/20260621_srr_spec/MANIFEST.md`

Primary artifacts:

- `results/20260621_srr_spec/Result4.txt`
- `results/20260621_srr_spec/architecture_contract.md`
- `results/20260621_srr_spec/architecture_contract.yaml`
- `results/20260621_srr_spec/test_summary.md`
- `results/20260621_srr_spec/one_batch_smoke.json`
- `results/20260621_srr_spec/smoke_report.md`

## Failures Or Caveats

- The fold0 job wrapper is only an interface placeholder in this spec pass. Formal fold0 training must be controlled by `prompts/tasks/20260621_srr_fold0.md`.
- The skeleton implements one retrieval scale for the minimal smoke path. The contract preserves the Result4 multi-scale retrieval design for the fold0 implementation.
- No Slurm job was submitted in this spec task.

## Human Approval Needed

None for the spec result. Validation submission/upload remains explicitly not authorized.

## Gate Decision

`GO_FOLD0`

The next task `prompts/tasks/20260621_srr_fold0.md` may be started.
