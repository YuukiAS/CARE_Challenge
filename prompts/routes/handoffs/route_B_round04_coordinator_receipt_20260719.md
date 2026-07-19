---
route_id: route_B
portfolio_round: round04
date: 2026-07-19
role: codex_coordinator_executable_receipt
status: PENDING_COORDINATOR_EXECUTION
planning_commit: 755e5919d472e3033c23ff7a848cac618aca1d34
planning_parent_main: 30098813522cecd98e60bcb99e2676b28c1a5461
route_B_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_review_commit: 17062b00edc3443aacefe8583568797a9f2655ba
planner_plan_blob: e6e31f772e2766ec79c466660fe8f56f14350d6f
planner_prompt_blob: 030c4ae0cb97bae1d661b40786bf3d7be78d930d
controller_contract_blob: fdb74c49634ba02a30b96979f185bd71fcf085c4
executor_plan_blob: 505b3a64d83b3d17cbc28ea7c0837d098665f821
critic_request_blob: 9911593bef8d8381e0df620bf22ca8c759e24186
planner_audit_blob: 6a9881f3eba630ec51ffed2b9ecb0ca0367262ed
tested_main_commit: PENDING
tested_origin_main: PENDING
tested_origin_route_B: PENDING
tested_origin_route_C: PENDING
working_tree_clean: PENDING
all_required_exit_codes_zero: false
completion_token: PENDING
---

# Route B Round04 Codex coordinator executable receipt

This file must be completed by a Codex coordinator in `/users/a/e/aereinh/CARE` after the final binding commit is on `origin/main`. The Planner has not executed these commands.

The coordinator must not edit the six planning files. A planning-blob change requires a new Planner handoff and a new critic cycle.

## Bound planning files

- `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`: `e6e31f772e2766ec79c466660fe8f56f14350d6f`
- `prompts/routes/route_B_round04_planner_prompt.md`: `030c4ae0cb97bae1d661b40786bf3d7be78d930d`
- `prompts/routes/route_B_round04_controller_contract.md`: `fdb74c49634ba02a30b96979f185bd71fcf085c4`
- `prompts/routes/route_B_round04_executor_plan.yaml`: `505b3a64d83b3d17cbc28ea7c0837d098665f821`
- `prompts/routes/route_B_round04_critic_request.md`: `9911593bef8d8381e0df620bf22ca8c759e24186`
- `prompts/routes/route_B_round04_planner_audit.md`: `6a9881f3eba630ec51ffed2b9ecb0ca0367262ed`

## Required command sequence

```bash
cd /users/a/e/aereinh/CARE
git fetch --all --prune
git status --short --branch
test "$(git branch --show-current)" = "main"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test "$(git rev-parse origin/route_B)" = "b9c7664da7cb1f1892fff37a4497722f31a0a96d"
test "$(git rev-parse origin/route_C)" = "17062b00edc3443aacefe8583568797a9f2655ba"

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python   scripts/ops/validate_executor_plan.py   prompts/routes/route_B_round04_executor_plan.yaml

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python - <<'PY'
from pathlib import Path
import subprocess
import yaml

plan_path = Path("prompts/routes/route_B_round04_executor_plan.yaml")
data = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
assert data["executor_count"] == 11
assert data["max_parallel"] == 2
assert data["required_planning_review_token"] == "ROUTE_B_ROUND04_PLANNING_READY_FOR_CONTROLLER"
assert data["route_evidence_ref"] == "b9c7664da7cb1f1892fff37a4497722f31a0a96d"

executors = data["executors"]
assert len(executors) == 11
ids = {entry["id"]: entry for entry in executors}
b10 = ids["B10_TERMINAL_ACCOUNTING_REVIEW_PACKET"]
assert b10["depends_on"] == []
assert b10["controller_terminal_finalizer"] is True
assert b10["prepare_wave_helper_exempt"] is True
assert b10["depends_on_successful_merge_receipts"] is False
assert b10["finalizer_dependency_policy"] == "afterany_all_started_attempts"

required_scenarios = {
    "B1 failure before B2",
    "B2 external blocker",
    "B7 external/matching blocker",
    "B8 CINE_REGISTRATION_BLOCKER without B9",
    "timeout",
    "preemption",
    "cancelled race loser",
    "successful B6 and B9",
}
observed = set(data["terminal_finalizer_contract"]["static_regression_scenarios"])
assert required_scenarios <= observed

for entry in executors:
    validator = entry["validator"]
    known_bad = entry["known_bad_contract"]
    assert validator["script_path"]
    assert validator["command"].startswith("/users/a/e/aereinh/CARE/envs/env_CARE/bin/python ")
    assert validator["input_path"] == entry["result_dir"]
    assert validator["report_file"].startswith(entry["result_dir"] + "/")
    assert validator["expected_exit_code"] == 0
    assert validator["success_token"] == entry["required_completion_token"]
    assert known_bad["matrix_path"]
    assert known_bad["matrix_command"].startswith("/users/a/e/aereinh/CARE/envs/env_CARE/bin/python ")
    assert known_bad["report_file"].startswith(entry["result_dir"] + "/")
    assert known_bad["runner_expected_exit_code"] == 0
    assert known_bad["validator_expected_exit_code_per_fixture"] == 1
    assert known_bad["expected_failure_keys"]
    assert known_bad["all_keys_required"] is True
    assert known_bad["unexpected_pass_is_failure"] is True

bound = {
    "prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md": "e6e31f772e2766ec79c466660fe8f56f14350d6f",
    "prompts/routes/route_B_round04_planner_prompt.md": "030c4ae0cb97bae1d661b40786bf3d7be78d930d",
    "prompts/routes/route_B_round04_controller_contract.md": "fdb74c49634ba02a30b96979f185bd71fcf085c4",
    "prompts/routes/route_B_round04_executor_plan.yaml": "505b3a64d83b3d17cbc28ea7c0837d098665f821",
    "prompts/routes/route_B_round04_critic_request.md": "9911593bef8d8381e0df620bf22ca8c759e24186",
    "prompts/routes/route_B_round04_planner_audit.md": "6a9881f3eba630ec51ffed2b9ecb0ca0367262ed",
}
for path, expected in bound.items():
    actual = subprocess.check_output(["git", "hash-object", path], text=True).strip()
    assert actual == expected, (path, actual, expected)
print("Route B Round04 structural and binding assertions passed")
PY

git diff --check

FILES=(
  prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
  prompts/routes/route_B_round04_planner_prompt.md
  prompts/routes/route_B_round04_controller_contract.md
  prompts/routes/route_B_round04_executor_plan.yaml
  prompts/routes/route_B_round04_critic_request.md
  prompts/routes/route_B_round04_planner_audit.md
  prompts/routes/portfolio_round04_routeC_review_and_routeB_revision_planner_update_20260719.md
)

if rg -n 'TBD|optional|as appropriate|if needed|choose best|Codex decide|controller decide|按需|视情况|自行决定' "${FILES[@]}"; then
  echo "blank authority found" >&2
  exit 1
fi

FORBIDDEN_ROOT='/overflow/htzhu/CARE'
if rg -n "$FORBIDDEN_ROOT" "${FILES[@]}"; then
  echo "forbidden workspace path found in planning files" >&2
  exit 1
fi

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python - <<'PY'
from pathlib import Path
import re
import yaml
data = yaml.safe_load(Path("prompts/routes/route_B_round04_executor_plan.yaml").read_text())
bad = []
def walk(node, path="root"):
    if isinstance(node, dict):
        for key, value in node.items():
            walk(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            walk(value, f"{path}[{index}]")
    elif isinstance(node, str) and any(tag in path.lower() for tag in ("command", "validator")):
        if re.search(r"(^|[;&|]\s*)python(?:3)?\s", node):
            bad.append((path, node))
walk(data)
assert not bad, bad
print("formal command interpreter scan passed")
PY

if rg -ni 'future[ -]work|optional future|Cine .*defer|registration .*defer|temporal .*defer|后续事项|仅smoke'   prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md   prompts/routes/route_B_round04_controller_contract.md   prompts/routes/route_B_round04_executor_plan.yaml; then
  echo "CineMA/registration/temporal deferral found" >&2
  exit 1
fi

test "$(rg -n 'CineMA|registration|temporal|SVF|SyN' "${FILES[@]}" | wc -l)" -ge 40
test -z "$(git status --porcelain)"
```

## Required result table

Replace every `PENDING` value below with the observed command, exit code and concise output. Every required exit must be `0`.

| Check | Command | Exit | Output/receipt |
|---|---|---:|---|
| fetch | `git fetch --all --prune` | PENDING | PENDING |
| branch/status | `git status --short --branch` and branch assertion | PENDING | PENDING |
| ref binding | HEAD/origin assertions | PENDING | PENDING |
| executor plan | `validate_executor_plan.py` | PENDING | PENDING |
| structure/binding | PyYAML assertion block | PENDING | PENDING |
| diff | `git diff --check` | PENDING | PENDING |
| blank authority | `rg` scan | PENDING | PENDING |
| forbidden workspace | `rg` scan | PENDING | PENDING |
| interpreter | formal command scan | PENDING | PENDING |
| Cine fidelity | non-deferral and coverage scan | PENDING | PENDING |
| clean tree | `git status --porcelain` | PENDING | PENDING |

## Completion fields to fill

```text
tested_main_commit:
tested_origin_main:
tested_origin_route_B:
tested_origin_route_C:
coordinator_identity:
executed_at_utc:
working_tree_clean:
all_required_exit_codes_zero:
completion_token:
```

Only after all checks pass, set:

```text
status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
all_required_exit_codes_zero: true
completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
```

This receipt does not authorize a controller or any downstream scientific action. It only opens the next independent planning critic rereview.
