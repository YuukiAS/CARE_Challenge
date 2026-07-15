#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path("/users/a/e/aereinh/CARE")
WORKTREE_ROOT = Path("/users/a/e/aereinh/CARE_worktrees")
ROUTES = ("route_A", "route_B", "route_C")


def run(args: list[str], cwd: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def main() -> int:
    errors: list[str] = []

    expected_files = [
        ROOT / "routes/README.md",
        ROOT / "routes/route_A/README.md",
        ROOT / "routes/route_B/README.md",
        ROOT / "routes/route_C/README.md",
        ROOT / "configs/routes/partition_routing.yaml",
        ROOT / "scripts/ops/create_route_worktrees.sh",
        ROOT / "scripts/ops/remove_route_worktrees.sh",
        ROOT / "scripts/ops/create_route_tmux_sessions.sh",
        ROOT / "scripts/ops/create_route_reviewer_worktree.sh",
        ROOT / "scripts/ops/route_status.sh",
        ROOT / "scripts/ops/apply_route_branch_reset.sh",
    ]
    for path in expected_files:
        if not path.exists():
            fail(f"missing {path}", errors)

    root_readme = (ROOT / "README.md").read_text()
    if "routes/README.md" not in root_readme:
        fail("root README does not point to routes/README.md", errors)

    routes_readme = (ROOT / "routes/README.md").read_text() if (ROOT / "routes/README.md").exists() else ""
    for day in ["7月15日", "7月16日", "7月17日", "7月18日", "7月19日", "7月20日", "7月21日", "7月22日", "7月23日", "7月24日", "7月25日", "7月26日", "7月27日"]:
        if day not in routes_readme:
            fail(f"routes README missing {day}", errors)

    routing = (ROOT / "configs/routes/partition_routing.yaml").read_text() if (ROOT / "configs/routes/partition_routing.yaml").exists() else ""
    for token in ["htzhulab", "a100-gpu", "volta-gpu", "gpu_access", "gpu:nvidia_a100-pcie-40gb:1", "gpu:tesla_v100-sxm2-16gb:1", "v100_compatibility_must_be_declared"]:
        if token not in routing:
            fail(f"partition routing missing {token}", errors)

    cleanup = (ROOT / "scripts/ops/apply_route_branch_reset.sh").read_text() if (ROOT / "scripts/ops/apply_route_branch_reset.sh").exists() else ""
    if "CARE_APPLY_REMOTE_BRANCH_RESET" not in cleanup:
        fail("cleanup script is not guarded by CARE_APPLY_REMOTE_BRANCH_RESET", errors)
    if "--force" in cleanup or "*" in cleanup:
        fail("cleanup script contains force push or wildcard", errors)

    tracked_and_untracked = run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], check=False)
    for rel in tracked_and_untracked.splitlines():
        if "deadline_rescue" in rel:
            fail(f"forbidden deadline_rescue path/name: {rel}", errors)

    try:
        setup_commit = run(["git", "rev-parse", "main"])
        for route in ROUTES:
            branch_ref = run(["git", "rev-parse", route], check=False)
            if not branch_ref:
                fail(f"missing branch {route}", errors)
                continue
            merge_base = run(["git", "merge-base", "main", route])
            if merge_base != setup_commit:
                fail(f"{route} does not share main setup commit; merge-base={merge_base}", errors)
            path = WORKTREE_ROOT / route
            if path.exists():
                branch = run(["git", "branch", "--show-current"], cwd=path)
                if branch != route:
                    fail(f"{path} is on {branch}, expected {route}", errors)
            else:
                fail(f"missing worktree {path}", errors)
    except Exception as exc:
        fail(str(exc), errors)

    if errors:
        print("ROUTE_SETUP_VALIDATION_FAILED")
        for err in errors:
            print(f"- {err}")
        return 1

    print("ROUTE_SETUP_VALIDATION_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
