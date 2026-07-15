#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
WORKTREE_ROOT="${WORKTREE_ROOT:-/users/a/e/aereinh/CARE_worktrees}"
APPLY="${CARE_REMOVE_ROUTE_WORKTREES:-0}"
ROUTES=(route_A route_B route_C)

cd "${CARE_ROOT}"

for route in "${ROUTES[@]}"; do
  path="${WORKTREE_ROOT}/${route}"
  if [[ ! -d "${path}/.git" && ! -f "${path}/.git" ]]; then
    echo "SKIP missing worktree ${path}"
    continue
  fi

  if [[ -n "$(git -C "${path}" status --porcelain)" ]]; then
    echo "ERROR: dirty worktree, refusing to remove: ${path}" >&2
    exit 1
  fi

  if [[ "${APPLY}" == "1" ]]; then
    git worktree remove "${path}"
  else
    echo "DRY-RUN git worktree remove ${path}"
  fi
done
