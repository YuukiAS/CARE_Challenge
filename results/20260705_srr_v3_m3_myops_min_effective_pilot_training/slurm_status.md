# Slurm Status

## Queue And Fallback

- Initial htzhulab submission: job `57928435`, pending with reason `(Resources)`, canceled before start.
- Fallback decision: `a100-gpu` had available GPU capacity while htzhulab was resource-pending; this follows the CARE compute fallback order.

## Runs

| job_id | partition | role | state | exit_code | elapsed | note |
| --- | --- | --- | --- | --- | ---: | --- |
| `57928455` | `a100-gpu` | 2400-step calibration attempt | `FAILED` | `2:0` | `00:21:54` | Training completed 2400 steps, but aggregator correctly failed `train_loop_seconds < 1800`. |
| `57944737` | `a100-gpu` | final 6000-step M3 pilot | `COMPLETED` | `0:0` | `00:41:46` | Aggregator reported `adequacy_decision: PASS`. |

## Final Evidence

- log: `logs/SRRv3M3Pilot_57944737_20260705_114616.log`
- optimizer_steps: `6000`
- train_loop_seconds: `2126.2185006489744`
- eval_cases: `12`
- validation_events: `20`
- completion_check: `M3_READY_FOR_REVIEW`
