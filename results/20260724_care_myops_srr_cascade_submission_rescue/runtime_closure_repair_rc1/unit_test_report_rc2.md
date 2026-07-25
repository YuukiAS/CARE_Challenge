# RC2 Repair Validation Report

Decision: `NEEDS_MONITOR`

Formal jobs submitted: `false`

Formal authorization gate: `NEEDS_REPAIR`

## Commands

- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/run_care_srr_cascade_rc2_preflight.py scripts/evaluation/orchestrate_care_srr_cascade_w3.py` -> exit 0
- `bash -n jobs/care_mm/preflight_care_srr_cascade_rc2.sh jobs/care_mm/precompute_care_srr_cascade_source_cache.sh jobs/care_mm/precompute_care_srr_cascade_anchor_cache.sh jobs/care_mm/run_care_srr_cascade_formal_training.sh` -> exit 0
- `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_runtime_rc1.py` -> exit 0, 6 passed, 1 warning
- `./envs/env_CARE/bin/python scripts/evaluation/run_care_srr_cascade_rc2_preflight.py --source-status --prototypes --schedules --local-checks --formal-dry-runs --gate` -> exit 2, fail-closed because source cache/prototype/asset-backed checks are not terminal PASS

## Slurm

Non-formal RC2 jobs only:

- `60539491` `CareSRRPre2H` htzhulab -> `COMPLETED`, exit `0:0`
- `60539496` `CareSRRPre2A` a100-gpu -> `PENDING`
- `60539497` `CareSRRAnchorH` htzhulab -> `PENDING`
- `60539492` `CareSRRAnchorA` a100-gpu -> `PENDING`
- `60539519` `CareSRRCacheH` htzhulab -> `PENDING`
- `60539522` `CareSRRCacheA` a100-gpu -> `PENDING`

## Current Gate Blockers

- anchor cache final dir is incomplete/stale until direct fallback race completes and publishes 220 files.
- source cache v2 is missing until tiled sliding-window source-cache race completes.
- prototype cache, real overfit, asset-backed augmentation fiducial, asset-backed loss gradients, and checkpoint hash roundtrip remain blocked on source/prototype cache.
- a100 GPU preflight is pending.

## RC2 Source-Cache v4 Repair (2026-07-24T19:35:07.159705+00:00)

- `bash -n jobs/care_mm/precompute_care_srr_cascade_source_cache.sh jobs/care_mm/preflight_care_srr_cascade_rc2.sh jobs/care_mm/run_care_srr_cascade_formal_training.sh` -> exit 0
- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/run_care_srr_cascade_rc2_preflight.py scripts/evaluation/orchestrate_care_srr_cascade_w3.py` -> exit 0
- `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_runtime_rc1.py` -> exit 0, 6 passed, 1 warning
- `sbatch --parsable --job-name=CareSRRCacheH2 --partition=htzhulab --qos=gpu_access --gres=gpu:1 --export=ALL,CACHE_ATTEMPT_ID=cache_htzhulab_rc2_v4,CACHE_RACE_GROUP=care_srr_cache_full_all220_20260725_rc2_v4,CARE_SOURCE_CACHE_PARITY_CASE_COUNT=4 jobs/care_mm/precompute_care_srr_cascade_source_cache.sh` -> `60546764`, current state `PENDING(Resources)`
- `sbatch --parsable --job-name=CareSRRCacheA2 --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 --export=ALL,CACHE_ATTEMPT_ID=cache_a100_rc2_v4,CACHE_RACE_GROUP=care_srr_cache_full_all220_20260725_rc2_v4,CARE_SOURCE_CACHE_PARITY_CASE_COUNT=4 jobs/care_mm/precompute_care_srr_cascade_source_cache.sh` -> `60546773`, current state `PENDING(Priority)`
- `squeue/sacct` monitor refresh -> `60539496` still `PENDING(Priority)`; no source-cache v4 winner lock yet.

Formal jobs submitted: `false`. Formal authorization gate remains `NEEDS_REPAIR` until source-cache v2, a100 preflight, prototype, asset-backed local checks, dry-runs, orchestrator, and known-bad suite are all PASS.
- `2026-07-24T19:36:21.390783+00:00` final source-cache wrapper default race group set to `care_srr_cache_full_all220_20260725_rc2_v4`; `bash -n jobs/care_mm/precompute_care_srr_cascade_source_cache.sh` -> exit 0; script sha256 `e33df71837850d4ad837e558030f41e68459a4d463a34cba8ce1e60c33384cdf`.

## RC2 Source-Cache v5 Repair (2026-07-24T20:16:01.452614+00:00)

- Diagnosed v4 parity failure: `padded_single_tile_direct_recompute_vs_sliding_window_cache` compared non-contract direct model forward against contract tiled sliding-window cache. Failing rows were logit fields for `Case1001` and `Case1002`; shape/dtype/finite/L2 checks passed, so the defect was comparator semantics, not cache serialization.
- Archived failed v4 winner lock to `results/20260724_care_myops_srr_cascade_submission_rescue/runtime/source_cache_v2.care_srr_cache_full_all220_20260725_rc2_v4.failed_60546764.winner.lock`.
- `bash -n jobs/care_mm/precompute_care_srr_cascade_source_cache.sh jobs/care_mm/preflight_care_srr_cascade_rc2.sh jobs/care_mm/run_care_srr_cascade_formal_training.sh` -> exit 0
- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/run_care_srr_cascade_rc2_preflight.py scripts/evaluation/orchestrate_care_srr_cascade_w3.py` -> exit 0
- `rg -n "direct_single_tile_forward|padded_single_tile_direct|whole_volume_forward" jobs/care_mm/precompute_care_srr_cascade_source_cache.sh` -> only historical failed-attempt note remains, no executable direct comparator
- `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_runtime_rc1.py` -> exit 0, 6 passed, 1 warning
- v5 source-cache race submitted: `60552238` htzhulab `PENDING(Resources)`, `60552252` a100-gpu `PENDING(Priority)`.
- a100 GPU preflight `60539496` remains `PENDING(Priority)`.

Formal jobs submitted: `false`. Formal authorization gate remains `NEEDS_REPAIR`.

## RC2 Source-Cache v6 Contract Selector Repair (2026-07-24T20:24:59.544073+00:00)

- Recorded v5 jobs `60552238` and `60552252` as `CANCELLED_NONCOMPLIANT_BY_CONTROLLER`; they are not source-cache evidence.
- Patched source-cache selector to read `source_cache.direct_parity` from `configs/care_mm/srr_cascade_runtime_closure_repair.yaml`: `minimum_cases=8`, required patterns `trimodal`, `LGE_C0`, `LGE_only`, thresholds `0.002` feature and `1e-5` logits.
- Local selector inventory: `trimodal=80`, `LGE_C0=24`, `LGE_only=116`; selected parity cases: `Case2001:trimodal`, `Case5001:LGE_C0`, `Case1001:LGE_only`, `Case1002:LGE_only`, `Case1003:LGE_only`, `Case1004:LGE_only`, `Case1005:LGE_only`, `Case1006:LGE_only`.
- `bash -n jobs/care_mm/precompute_care_srr_cascade_source_cache.sh jobs/care_mm/preflight_care_srr_cascade_rc2.sh jobs/care_mm/run_care_srr_cascade_formal_training.sh` -> exit 0
- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/run_care_srr_cascade_rc2_preflight.py scripts/evaluation/orchestrate_care_srr_cascade_w3.py` -> exit 0
- `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_runtime_rc1.py` -> exit 0, 6 passed, 1 warning
- v6 source-cache race submitted: `60552895` htzhulab `PENDING(Resources)`, `60552903` a100-gpu `PENDING(Priority)`.
- a100 GPU preflight `60539496` remains `PENDING(Priority)`.

Formal jobs submitted: `false`. Formal authorization gate remains `NEEDS_REPAIR`.



## Prototype Source Eligibility Repair (2026-07-25T00:53:49.208314+00:00)

Commands:
- `kill -TERM 378032` -> process exited; old stuck prototype attempt stopped.
- `kill -TERM 384748` -> process exited; early stuck retry stopped.
- `kill -TERM 389493` -> process exited; local-check run stopped during stale gate cache-hash reread after dependent receipts had refreshed.
- `kill -TERM 392749` -> process exited; gate run stopped during stale anchor cache-hash reread.
- `./envs/env_CARE/bin/python -m py_compile scripts/evaluation/run_care_srr_cascade_rc2_preflight.py src/care_myocardium/srr_production/case_prototypes.py` -> exit 0.
- `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_rescue.py tests/care_mm/test_care_srr_cascade_runtime_rc1.py -q` -> 17 passed, 1 warning.
- `./envs/env_CARE/bin/python -u scripts/evaluation/run_care_srr_cascade_rc2_preflight.py --prototypes` -> exit 0, prototype PASS.
- `./envs/env_CARE/bin/python -u scripts/evaluation/run_care_srr_cascade_rc2_preflight.py --gate` -> exit 2 expected fail-closed because a100 GPU preflight is still pending.

Repair evidence:
- `prototype_cache_status_v2.json`: PASS, 220 prototype files, 220 manifest cases, 440 crossfit rows, edema no-T2 source records in bank = 0, no-T2 edema queries skipped = 140, eligible edema queries = 80.
- `prototype_cache_manifest_v2.csv`: 1066 rows, all PASS.
- `prototype_crossfit_checks_v2.csv`: 440 rows, all PASS, source eligibility rule recorded for edema banks.
- `formal_authorization_gate.json`: decision NEEDS_REPAIR, blocker only `gpu_preflight`; formal_jobs_authorized=false.

Current Slurm:
- `60552895` htzhulab source-cache v6 COMPLETED/PASS, exit 0:0, elapsed 00:07:56.
- `60552903` a100 source-cache v6 mirror CANCELLED by Controller after htzhulab PASS.
- `60539496` a100 GPU preflight remains PENDING(Priority); formal gate cannot PASS.
