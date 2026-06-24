# Setup 20260621 SRR Fold0

## Dependency

- Required spec result: `results/20260621_srr_spec/result.md`
- Observed gate: `GO_FOLD0`

## Variants

| variant | purpose | script | short wiring job | corrected formal job |
| --- | --- | --- | --- | --- |
| `conditional_dualhead_control` | availability-aware late-fusion control with separate anatomy/scar/edema heads and T2-masked edema supervision, no retrieval gate | `jobs/src/run_srr_myops_fold0_conditional.sh` | `55720659` | `55723114` |
| `srr_minimal` | Result4 shared/private selective representation retrieval with the same heads and loss contract | `jobs/src/run_srr_myops_fold0_srr.sh` | `55720658` | `55723115` |

## Shared Training Budget

- partition: `htzhulab`
- walltime: `06:00:00` per job
- GPU: `--gres=gpu:1`
- batch size: `2`
- patch shape: `12,96,96`
- max runtime inside Python: `16200` seconds
- max steps: `500000` (guard only; expected stop is max runtime)
- validation cadence: every `5000` steps
- complete-case oversampling: `0.55`
- foreground oversampling: `0.75`

## Output Roots

- `results/20260621_srr_fold0/variants/conditional_dualhead_control/`
- `results/20260621_srr_fold0/variants/srr_minimal/`
- combined reports: `results/20260621_srr_fold0/`

## Constraints

- No validation submission or upload-ready package.
- No folds 1-4.
- No external data, network, or external weights.
- No third-party baseline patching.
- No no-T2 edema hard-negative dense supervision.
