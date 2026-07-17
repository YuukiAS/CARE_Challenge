# Route B Independent Review

decision: `ROUTE_B_REVIEW_NEEDS_REVISION`

This is a read-only reviewer decision on the committed Route B controller packet at `0200e86f7a95ff9753f9c425419052e878d342f4` (`Finalize Route B adequacy recovery packet`). This decision is not route promotion, not hosted metric readiness, and not a final scientific conclusion.

## Findings

1. `ROUTE_B_READY_FOR_REVIEW` is supported by terminal post-freeze bounded train/eval evidence rather than by a submitted-only monitor packet. `sacct` independently confirmed winner job `59364846` on `htzhulab` as `COMPLETED`, `ExitCode=0:0`, elapsed `00:32:02`, node `g180702`; loser jobs `59364845` on `a100-gpu` and `59364847` on `volta-gpu` were `CANCELLED by 397557` with no running or pending state.

2. The tracked adequacy files support the controller's recovery claim. `training_adequacy.csv` reports `25000` optimizer steps, `1908.338` train-loop seconds, `2` validation events, `10` MyoPS eval cases, `5` Cine eval cases, loss decrease from `2.432160` to `0.001281`, cache isolation under `results/route_B/runtime/bounded_train_eval`, and same-split anchor baseline availability. `bounded_train_eval_summary.json`, `metrics_summary.csv`, and `case_safety_matrix.csv` are present and consistent with those counts.

3. Terminal aggregation is present in tracked lightweight files. `bounded_train_eval_summary.json` records aggregation exit code `0` and lists updates to `bounded_train_eval_summary.json`, `training_adequacy.csv`, `metrics_summary.csv`, `case_safety_matrix.csv`, `completion_check.md`, `controller_report.md`, `result.md`, and `review_request.md`. `MANIFEST.md` lists the expected lightweight packet files.

4. The packet is mostly self-consistent about review boundaries. `controller_report.md`, `controller_context.json`, and `finalizer_state.json` all keep `route_promotion_decision: NOT_REVIEWED`, `route_negative_decision: NOT_REVIEWED`, and `scientific_resolution_status: AWAITING_REVIEW`; `finalizer_state.json` records `push_performed: false` and `review_md_written: false`. No exact forbidden token was found in `results/route_B`.

5. Revision is required because the validator contract is materially under-covered. The rerun strict validators exit `0`, but `validate_route_b_packet.py` only checks required file presence, forbidden exact tokens, one completion token in `completion_check.md`, a minimal implementation-gate pass, monitor language only in `completion_check.md`, and staged heavy artifacts. It does not parse `training_adequacy.csv`, `bounded_train_eval_summary.json`, Slurm terminal accounting, aggregation outputs, `commands_run.md`, `result.md`, or controller/finalizer consistency. A ready packet could therefore pass while omitting or weakening the post-freeze training evidence that this review had to verify manually.

6. Revision is also required because known-bad coverage does not match the Route B contract. The committed known-bad fixtures are only `ready_with_missing_modules`, `formal_training_before_gate`, `monitor_packet_claims_completion`, and `external_blocker_without_code_gate`. The contract requires fail-closed coverage for mock/config/CSV-only modules, old wrapper bypass, unavailable-modality gradient/perturbation failures, router ignorance of image features/availability, prototype leakage, no-T2 edema negative supervision, no-effect proposal/refiner/gate paths, residual identity/bounds failures, Cine frame0/descriptor/topology/proxy paths, temporal registered-tensor consumption failures, undertrained ready claims, heavy artifacts, and forbidden upload/promotion/M11/cross-route claims. Those semantic bypasses are not covered by the current fixture set.

7. There is a residual self-consistency issue in validator reporting: the implementation validator report still returns `token: ROUTE_B_SCIENTIFIC_UNDERTRAINED` while final packet files report `ROUTE_B_READY_FOR_REVIEW` after adequacy recovery. This is explainable as an implementation-gate-only validator, but the report naming is stale enough to confuse downstream automated checks.

8. The reviewer prompt required reading `prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md`, but that file does not exist at this HEAD. I searched for anti-laziness materials and found only older task-level SRR-v2.5 anti-laziness prompts/scripts, not the requested Route-specific protocol path. This should be corrected or the reviewer prompt should be updated to the actual canonical file.

## Verification Commands Run

- `pwd`
- `git status --short --branch`
- `git rev-parse HEAD`
- `git show --stat --oneline --decorate 0200e86`
- `git ls-tree -r --name-only HEAD results/route_B`
- `sacct -j 59364845,59364846,59364847 --format=JobIDRaw,JobName%30,Partition,State,ExitCode,Elapsed,Start,End,NodeList -P`
- `python -m json.tool results/route_B/bounded_train_eval_summary.json`
- `python -m json.tool results/route_B/controller_context.json`
- `python -m json.tool results/route_B/finalizer_state.json`
- `python -m json.tool results/route_B/validator_packet_report.json`
- `python -m json.tool results/route_B/validator_implementation_report.json`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B/validate_route_b_packet.py --strict --write-report results/route_B/validator_packet_report.json`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B/validate_route_b_implementation.py --strict --write-report results/route_B/validator_implementation_report.json`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python -m pytest -q tests/route_B src/care_myocardium/tests/test_route_b_implementation.py`
- `git diff --check`

Validator reruns produced no tracked diff. Pytest result: `3 passed in 4.66s`. `git diff --check` exited `0`.

## Forbidden Actions

Not performed: code fixes, controller packet repair, training, Slurm submission, validation packaging, validation upload, hosted metric claim, route promotion, final scientific conclusion, M11 start, cross-route merge, push, or Route A/C access.
