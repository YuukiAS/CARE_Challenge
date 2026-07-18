# Route B Round03 Independent Review

decision: `ROUTE_B_ROUND03_REVIEW_NEEDS_REVISION`

Reviewed commit: `32c82d5616b740066a1a5c97c7ecdeaab89dea9f` (`Route B round03 terminal packet`)

Role boundary: independent reviewer only. I did not train, submit or cancel Slurm jobs, edit code or controller packet files, upload validation, push, promote a route, start M11, merge routes, claim hosted metrics, or make a final scientific decision.

## Findings

1. `ROUTE_B_ROUND03_REVIEW_NEEDS_REVISION` is required because the credited B3 terminal run does not faithfully implement the Route B Round03 sampler contract. The route contract requires every four optimizer steps to draw `E,E,S,R` with replacement from the frozen strata. The tracked final B3 completion reports `sampler_counts={'E': 1586, 'S': 7420, 'R': 53340}` over `62346` optimizer steps, which is not compatible with the required 2:1:1 draw schedule. Code inspection confirms `scripts/training/route_B_round03/train_myops.py` cycles through `myops_fold0_primary_44.json` via `cache.get(step - 1, seed=step)` and only labels the observed case after selection; it does not consume `myops_sampler_strata.json` or the fixed `E,E,S,R` draw cycle. Therefore the B3 gate failure is real runtime evidence, but not a faithful scientific gate failure under the reviewed contract.

2. The apparent B3 negative signal is not candidate-ready and not adequate-negative evidence. Final attempt `59457115` did meet the numeric runtime floors recorded in the packet (`62346` optimizer steps, `1801.4200326240389` train-loop seconds, `32` validation events), but it failed `anatomy_union_overfit=false`; the metrics remain zero across validation events (`scar_dice_mean=0.0`, `edema_dice_mean=0.0`, `anatomy_union_overfit_dice=0.0`). Because the sampler semantics were wrong, this should return to controller revision rather than move to planner/portfolio judgment as an adequate negative.

3. B4-B9 absence is contract-allowed only if the B3 stop is a faithful terminal scientific gate failure. The executor plan makes B3 blocking and forbids advancing after `ROUTE_B_ROUND03_B3_SCIENTIFIC_GATE_FAILED`, so the missing B4-B9 packets are structurally explainable. However, because the B3 credited run violated the sampler contract, the downstream absence remains a consequence of a defective B3 stage, not a clean adequate-negative terminal class.

4. The B10 packet validator is too weak for the contract it claims. I reran `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round03/validate_packet.py --strict --require-all-attempt-accounting results/route_B/round03/executors/B10`, and it exited `PASS`, but code inspection shows the `--require-all-attempt-accounting` flag is parsed and never used to compare `controller_ledger.csv`/`routing_ledger.csv` against Slurm accounting. The validator also does not check sampler-ratio semantics, B3 training adequacy semantics, B10 finalizer dependency coverage, architecture validator rows, or `git diff --check` evidence inside the packet. The reviewer could verify some accounting manually, but the packet validator is not fail-closed enough for Round03.

5. Live Slurm accounting for the requested B3 jobs is terminal and broadly matches the ledger. `sacct` confirms `59452967` and `59452969` cancelled pending, `59452968` failed on `volta-gpu` with `ExitCode=1:0`, `59453903` cancelled pending, `59453904` failed on `htzhulab` with `ExitCode=2:0`, `59457115` failed on `htzhulab` with `ExitCode=2:0`, and `59457116` cancelled pending. A full ledger query over all recorded B3 job IDs also found only terminal `FAILED` or `CANCELLED by 397557` states, so this is not `NEEDS_MONITOR`.

6. V100 and L40 attempts do not by themselves require a new scientific decision, but they do require cleaner validator/routing discipline. The V100 no-kernel-image failure is correctly recorded as zero-credit operational incompatibility in `results/route_B/round03/executors/B3/failed_winner_59452968.json`, and later compatible `htzhulab` attempts superseded it. L40 attempts are recorded as zero-credit non-default fallbacks and cancelled before start. These are not terminal blockers after live accounting, but future packets should have machine-checked partition compatibility and all-attempt accounting rather than relying on reviewer reconstruction.

7. I found no evidence of forbidden publication actions or tracked heavy artifacts. The controller packet keeps promotion, route-negative, hosted metric, M11, cross-route merge, upload, push, and final scientific decision fields false/not reviewed. `git ls-files results/route_B` shows no tracked `.pt`, `.pth`, `.nii`, `.nii.gz`, `.zip`, `.safetensors`, or checkpoint artifacts; runtime checkpoints and logs remain ignored.

8. There is a packet-binding weakness: B10 `finalizer_state.json` and `completion.json` record `git_head` as `a4f5799647a7ea406d5e23be0a6378571e7cae82`, while the review target is the committed terminal packet at `32c82d5616b740066a1a5c97c7ecdeaab89dea9f`. This is understandable if aggregation ran before the local packet commit, but the Round03 finalizer contract expects review-ready receipts to bind the committed lightweight packet state. This should be repaired with the sampler and validator revisions.

## Verification Commands Run

- `pwd`
- `git status --short --branch`
- `git rev-parse HEAD`
- `git show --stat --oneline HEAD`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round03/validate_packet.py --strict --require-all-attempt-accounting results/route_B/round03/executors/B10`
- `sacct -j 59452967,59452968,59452969,59453903,59453904,59457115,59457116 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList%30,Start,End -P`
- `sacct -j 59451083,59451089,59451468,59451848,59451918,59452474,59452498,59452778,59452967,59452968,59452969,59453051,59453052,59453374,59453903,59453904,59453905,59456643,59456644,59457075,59457076,59457115,59457116 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,NodeList%30,Start,End -P`
- `git diff --check HEAD`
- `/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/validation/route_B_round03/validate_stage.py --stage evidence_warmup --strict results/route_B/round03/executors/B3`
- read-only inspection of the required Route B contract, executor plan, controller packet, B0/B1/B2/B3/B10 receipts, aggregation script, packet validator, job wrappers, final B3 runtime summary/logs, and tracked/ignored artifact state.

`validate_packet.py` passed, `git diff --check HEAD` passed, and `validate_stage.py` correctly failed B3 with `completion_token_not_pass`, `status_not_pass`, and `gate_check_failed:anatomy_union_overfit`.

## Next Actor

Return Route B to the controller for revision. The minimum revision scope is to implement and validate the frozen `E,E,S,R` sampler semantics in B3, strengthen B3/B10 validators to fail on sampler-ratio and all-attempt-accounting defects, refresh the finalizer packet binding to the committed packet HEAD, and then rerun the same B3 gate under the reviewed contract. This review does not authorize planner/portfolio adequate-negative judgment yet.
