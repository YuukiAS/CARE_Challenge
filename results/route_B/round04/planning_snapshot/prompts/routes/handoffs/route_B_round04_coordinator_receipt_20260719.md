---
route_id: route_B
portfolio_round: round04
date: '2026-07-20'
role: codex_coordinator_executable_receipt
status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
planning_commit: 38551ed98a42b005a1a3f0b793efdef700037ee8
planning_parent_main: 64f5a27298cb2efd1f576a70296e49388ab0b717
route_B_evidence_commit: b9c7664da7cb1f1892fff37a4497722f31a0a96d
route_C_evidence_commit: 17062b00edc3443aacefe8583568797a9f2655ba
six_planning_blobs:
  prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md: a537e0e86e3059efa27d128ac3a018a22a6a40aa
  prompts/routes/route_B_round04_planner_prompt.md: 1ea2277d20f9e4eab1711c767274204342c372e2
  prompts/routes/route_B_round04_controller_contract.md: 3087283d65dbb6eeca697a393fc545528fe7fada
  prompts/routes/route_B_round04_executor_plan.yaml: c5e437a0cd847ade5244727a43c239da9825c737
  prompts/routes/route_B_round04_critic_request.md: fcac92428b38d4b10e21e3ff594b83cac7eeba60
  prompts/routes/route_B_round04_planner_audit.md: 7a7964867557fb8f43a236d4aefecfd6174a7b4c
tested_commit_policy: exact_current_main_or_ancestor_with_allowlisted_diff_and_unchanged_six_blobs
allowed_descendant_paths:
- prompts/routes/handoffs/CURRENT.md
- prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
- prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
- prompts/routes/route_B_round04_critic_rereview.md
- prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
- docs/figures/round03_route_architecture/**
- controller_notifications/**
- scripts/ops/build_route_watchboard.py
- tests/ops/test_build_route_watchboard.py
- tests/ops/test_controller_notifications.py
tested_main_commit: 41decbb95ebe1b02d9d5d836ae3455dfb0469f1f
tested_origin_main: 41decbb95ebe1b02d9d5d836ae3455dfb0469f1f
tested_origin_route_B: b9c7664da7cb1f1892fff37a4497722f31a0a96d
tested_origin_route_C: 17062b00edc3443aacefe8583568797a9f2655ba
working_tree_clean: true
all_required_exit_codes_zero: true
completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
---

# Route B Round04 Codex coordinator executable receipt

This receipt was completed by the Codex coordinator in an isolated `origin/main` worktree. The Planner did not execute these commands. The previous pending receipt is superseded because the six planning blobs changed.

## Bound files

- `prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md`: `a537e0e86e3059efa27d128ac3a018a22a6a40aa`
- `prompts/routes/route_B_round04_planner_prompt.md`: `1ea2277d20f9e4eab1711c767274204342c372e2`
- `prompts/routes/route_B_round04_controller_contract.md`: `3087283d65dbb6eeca697a393fc545528fe7fada`
- `prompts/routes/route_B_round04_executor_plan.yaml`: `c5e437a0cd847ade5244727a43c239da9825c737`
- `prompts/routes/route_B_round04_critic_request.md`: `fcac92428b38d4b10e21e3ff594b83cac7eeba60`
- `prompts/routes/route_B_round04_planner_audit.md`: `7a7964867557fb8f43a236d4aefecfd6174a7b4c`

## Unified tested-commit rule

The tested commit must equal current `origin/main`, or be its ancestor with a complete descendant diff limited to:

```text
prompts/routes/handoffs/CURRENT.md
prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md
prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md
prompts/routes/route_B_round04_critic_rereview.md
prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md
docs/figures/round03_route_architecture/**
controller_notifications/**
scripts/ops/build_route_watchboard.py
tests/ops/test_build_route_watchboard.py
tests/ops/test_controller_notifications.py
```

All six blobs must remain unchanged under either relation.

## Required command sequence

```bash
cd /users/a/e/aereinh/CARE
git fetch --all --prune
git status --short --branch
test "$(git branch --show-current)" = "main"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
test "$(git rev-parse origin/route_B)" = "b9c7664da7cb1f1892fff37a4497722f31a0a96d"
test "$(git rev-parse origin/route_C)" = "17062b00edc3443aacefe8583568797a9f2655ba"

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/ops/validate_executor_plan.py prompts/routes/route_B_round04_executor_plan.yaml

/users/a/e/aereinh/CARE/envs/env_CARE/bin/python - <<'PY'
from pathlib import Path
import re, subprocess, yaml

handoff_path=Path("prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md")
receipt_path=Path("prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md")
plan_path=Path("prompts/routes/route_B_round04_executor_plan.yaml")
current_path=Path("prompts/routes/handoffs/CURRENT.md")
critic_request=Path("prompts/routes/route_B_round04_critic_request.md")
planner_audit=Path("prompts/routes/route_B_round04_planner_audit.md")

def fm(path):
    text=path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), path
    return yaml.safe_load(text.split("---",2)[1])

handoff=fm(handoff_path)
receipt=fm(receipt_path)
plan=yaml.safe_load(plan_path.read_text(encoding="utf-8"))
expected=handoff["six_planning_blobs"]
assert expected == receipt["six_planning_blobs"]
assert handoff["planning_commit"] == "38551ed98a42b005a1a3f0b793efdef700037ee8"
assert plan["executor_count"] == 11
assert plan["controller_start_authorized"] is False
assert plan["tested_commit_policy"]["allowed_descendant_paths"] == handoff["allowed_descendant_paths"]
assert receipt["allowed_descendant_paths"] == handoff["allowed_descendant_paths"]

for path, blob in expected.items():
    actual=subprocess.check_output(["git","hash-object",path],text=True).strip()
    assert actual == blob, (path,actual,blob)

mat=plan["controller_planning_materialization"]
assert mat["controller_worktree"] == "/users/a/e/aereinh/CARE_worktrees/route_B"
assert mat["source_main_worktree"] == "/users/a/e/aereinh/CARE"
assert mat["snapshot_root"] == "results/route_B/round04/planning_snapshot"
assert mat["manifest_path"].endswith("/MANIFEST.json")
assert mat["hash_audit_path"].endswith("/hash_audit.json")
assert mat["descendant_diff_audit_path"].endswith("/descendant_diff_audit.json")
assert mat["receipt_path"].endswith("/materialization_receipt.json")
assert mat["failure_token"] == "ROUTE_B_ROUND04_B0_STALE_PLANNING_BINDING"
assert mat["atomic_publish"] is True
assert mat["final_snapshot_read_only"] is True
assert mat["no_code_or_slurm_before_pass"] is True
assert mat["materialization_command"].startswith("bash -lc ")
assert "/users/a/e/aereinh/CARE/envs/env_CARE/bin/python" in mat["materialization_command"]
assert "validate_planning_snapshot.py" not in mat["materialization_command"]

ids={e["id"]:e for e in plan["executors"]}
b0=ids["B0_REBIND_EVIDENCE_MANIFEST_BASELINE"]
for path in (
    "prompts/routes/route_B_round04_critic_rereview.md","prompts/routes/handoffs/route_B_round04_critic_handoff_20260719.md","prompts/routes/handoffs/route_B_round04_coordinator_receipt_20260719.md","prompts/routes/handoffs/CURRENT.md","prompts/routes/portfolio_round04_route_C_followup_decision_20260719.md"
):
    assert path in b0["current_gate_inputs"], path
assert b0["superseded_historical_inputs"] == ["prompts/routes/route_B_round04_critic_review.md"]
for key in (
    "STALE_PLANNING_BINDING","PLANNING_SOURCE_UNREADABLE",
    "PLANNING_SNAPSHOT_INCOMPLETE","PLANNING_SNAPSHOT_HASH_MISMATCH",
    "CURRENT_REREVIEW_MISSING_OR_NOT_READY",
    "CURRENT_COORDINATOR_RECEIPT_MISSING_OR_STALE",
    "DISALLOWED_MAIN_DESCENDANT_PATH"
):
    assert key in b0["known_bad_contract"]["expected_failure_keys"]

b10=ids["B10_TERMINAL_ACCOUNTING_REVIEW_PACKET"]
assert b10["depends_on"] == []
assert b10["controller_terminal_finalizer"] is True
assert b10["prepare_wave_helper_exempt"] is True
assert b10["depends_on_successful_merge_receipts"] is False
assert b10["finalizer_dependency_policy"] == "afterany_all_started_attempts"

for e in plan["executors"]:
    v=e["validator"]; k=e["known_bad_contract"]
    assert v["command"].startswith("/users/a/e/aereinh/CARE/envs/env_CARE/bin/python ")
    assert v["expected_exit_code"] == 0
    assert k["matrix_command"].startswith("/users/a/e/aereinh/CARE/envs/env_CARE/bin/python ")
    assert k["runner_expected_exit_code"] == 0
    assert k["validator_expected_exit_code_per_fixture"] == 1
    assert k["expected_failure_keys"]
    assert k["all_keys_required"] is True
    assert k["unexpected_pass_is_failure"] is True

assert critic_request.read_text(encoding="utf-8").find("six_planning_blob_binding_source") >= 0
assert planner_audit.read_text(encoding="utf-8").find("six_planning_blob_binding_source") >= 0
assert "controller_authorized_now: 0" in current_path.read_text(encoding="utf-8")
print("Route B Round04 planning revision structural checks passed")
PY

git diff --check

FILES=(
  prompts/routes/portfolio_round04_route_B_planner_plan_20260719.md
  prompts/routes/route_B_round04_planner_prompt.md
  prompts/routes/route_B_round04_controller_contract.md
  prompts/routes/route_B_round04_executor_plan.yaml
  prompts/routes/route_B_round04_critic_request.md
  prompts/routes/route_B_round04_planner_audit.md
)
if rg -n 'TBD|optional|as appropriate|if needed|choose best|Codex decide|controller decide|按需|视情况|自行决定' "${FILES[@]}"; then
  exit 1
fi
if rg -n '/overflow/htzhu/CARE' "${FILES[@]}"; then
  exit 1
fi
test -z "$(git status --porcelain)"
```

## Required result table

Every row must be completed with observed command, exit and concise output. Every required exit must be `0`.

| Check | Command | Exit | Output |
|---|---|---:|---|
| fetch | `git fetch --all --prune` | 0 | `origin/main` at `41decbb95ebe1b02d9d5d836ae3455dfb0469f1f`; Route B/C refs unchanged. |
| branch/status | branch and clean-tree assertions | 0 | Isolated worktree checked from `origin/main`; no unrelated local changes included. |
| refs | main/Route B/Route C assertions | 0 | `origin/route_B=b9c7664da7cb1f1892fff37a4497722f31a0a96d`; `origin/route_C=17062b00edc3443aacefe8583568797a9f2655ba`. |
| executor plan | `validate_executor_plan.py` | 0 | `executor plan validation passed`. |
| six blobs | `git hash-object` assertions | 0 | All six planning blobs match handoff and receipt hashes. |
| materialization | schema/self-contained command assertions | 0 | `controller_planning_materialization` is present, route_B/read-only-main/snapshot bound, atomic, read-only after publish, and fail-closed. |
| B0 inputs | current/superseded input assertions | 0 | B0 current inputs include current rereview, handoff, receipt, CURRENT and Route C hold; old critic review is superseded historical only. |
| ancestor policy | CURRENT/handoff/receipt/request/contract/plan consistency | 0 | Unified exact-current-or-ancestor-with-allowlisted-diff policy is consistent. |
| B10 | terminal finalizer assertions | 0 | B10 is controller-owned, `depends_on: []`, `afterany_all_started_attempts`, with no successful-merge dependency. |
| validators | B0-B10 exact validator/known-bad assertions | 0 | All executor validators and known-bad matrices use the CARE Python path, expected exits, and required failure keys. |
| diff | `git diff --check` | 0 | No whitespace errors. |
| blank authority | forbidden delegation scan | 0 | No forbidden planner blanks or controller-delegation phrases in the six planning files. |
| forbidden path | workspace path scan | 0 | No `/overflow/htzhu/CARE` path in the six planning files. |
| clean tree | `git status --porcelain` | 0 | Clean after committing this receipt-only fix; final commit is an allowlisted descendant of tested `41decbb`. |

Every row above passed. This receipt sets:

```text
status: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
working_tree_clean: true
all_required_exit_codes_zero: true
completion_token: READY_FOR_ROUTE_B_ROUND04_CRITIC_REREVIEW
```

This receipt opens only the next independent planning critic rereview. It authorizes no Controller or downstream scientific action.
