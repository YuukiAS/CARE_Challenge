# Route C commands run

```text
git status --short --branch
## route_C
```

```text
python scripts/ops/validate_executor_plan.py prompts/routes/route_C_executor_plan.yaml
executor plan validation passed
```

```text
python scripts/ops/prepare_care_executor_wave.py --plan prompts/routes/route_C_executor_plan.yaml --wave 1 --receipt-path results/route_C/executor_waves/wave_1/prepare_dry_run_receipt.json --allow-subagent-launch --dry-run
LAUNCH_EXECUTORS
```

No Slurm job has been submitted during C1 bootstrap. No validation package has been created or uploaded.

```text
python scripts/ops/prepare_care_executor_wave.py --plan prompts/routes/route_C_executor_plan.yaml --wave 1 --receipt-path results/route_C/executor_waves/wave_1/prepare_receipt.json --allow-subagent-launch
LAUNCH_EXECUTORS
```

This created:

```text
/users/a/e/aereinh/CARE_worktrees/route_C_executors/myops_evidence
/users/a/e/aereinh/CARE_worktrees/route_C_executors/cine_fidelity
```

```text
AI_RESEARCH_TOOLKIT_ROOT=/overflow/htzhu/mingcheng_new/AI_Research_Toolkit python scripts/architecture/run_toolkit_healthcheck.py --check --output results/route_C/toolkit_healthcheck.json
toolkit healthcheck passed: results/route_C/toolkit_healthcheck.json
```

```text
python -m pytest tests/route_C/test_validate_controller_packet.py
3 passed
```

```text
git merge --no-ff codex/route_C/myops_evidence -m "Merge Route C MyoPS executor lane"
# merged MyoPS lane at e7b57d9fdb1499e57b2533161dff625b9631d050
```

```text
git merge --no-ff codex/route_C/cine_fidelity -m "Merge Route C Cine executor lane"
# merged Cine lane at 8c023a85da8b4a5ca36f48e0189a9eadd919e0d4
```

```text
python scripts/validation/route_C/validate_controller_packet.py --packet-root results/route_C
route_C controller packet validation passed
```

```text
python -m pytest tests/route_C/test_validate_controller_packet.py tests/route_C/myops/test_lane_validator.py tests/route_C/cine/test_fidelity_adapters.py
9 passed
```

```text
python scripts/validation/route_C/myops/validate_lane_packet.py --strict
exit 0
```

```text
python scripts/validation/route_C/cine/strict_validator.py --packet-dir results/route_C/executors/cine --write-report results/route_C/executors/cine/strict_validator_report.md
exit 0
```

```text
python scripts/validation/route_C/myops/validate_lane_packet.py --known-bad-selftest --strict
exit 0
```

```text
python scripts/validation/route_C/cine/known_bad_selftest.py
exit 0
```

```text
git diff --check
exit 0
```
