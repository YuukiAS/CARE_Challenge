#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
WORKTREE_ROOT="${WORKTREE_ROOT:-/users/a/e/aereinh/CARE_worktrees}"
ROUTES=(route_A route_B route_C)

cd "${CARE_ROOT}"

echo "main_sha=$(git rev-parse main)"
echo "origin_main_sha=$(git rev-parse origin/main 2>/dev/null || true)"
echo

for route in "${ROUTES[@]}"; do
  echo "== ${route} =="
  if git show-ref --verify --quiet "refs/heads/${route}"; then
    echo "sha=$(git rev-parse "${route}")"
    echo "ahead_behind_main=$(git rev-list --left-right --count main..."${route}")"
  else
    echo "sha=MISSING_BRANCH"
  fi
  path="${WORKTREE_ROOT}/${route}"
  if [[ -d "${path}/.git" || -f "${path}/.git" ]]; then
    echo "worktree=${path}"
    echo "branch=$(git -C "${path}" branch --show-current)"
    echo "dirty=$(git -C "${path}" status --porcelain | wc -l | tr -d ' ')"
  else
    echo "worktree=MISSING"
  fi
  [[ -d "results/${route}" ]] && echo "result_dir=present" || echo "result_dir=missing"
  echo
done

echo "== tmux =="
for session in care_portfolio care_route_A_controller care_route_B_controller care_route_C_controller care_route_A_reviewer care_route_B_reviewer care_route_C_reviewer; do
  if tmux has-session -t "${session}" 2>/dev/null; then
    echo "${session}=present"
  else
    echo "${session}=missing"
  fi
done

echo
echo "== Slurm route jobs =="
squeue -h -o '%i|%P|%T|%j' 2>/dev/null | awk -F'|' '/route_A|route_B|route_C/ {print}' || true

echo
echo "== Partition summary =="
sinfo -o '%P|%a|%l|%D|%t|%G' 2>/dev/null | awk -F'|' '/htzhulab|a100-gpu|volta-gpu/ {print}' || true
