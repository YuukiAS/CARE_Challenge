#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
WORKTREE_ROOT="${WORKTREE_ROOT:-/users/a/e/aereinh/CARE_worktrees}"
ROUTES=(route_A route_B route_C)

cd "${CARE_ROOT}"

if [[ "$(git branch --show-current)" != "main" ]]; then
  echo "ERROR: create route worktrees from main only" >&2
  exit 1
fi

if ! git diff --quiet HEAD || ! git diff --cached --quiet; then
  echo "ERROR: tracked main worktree changes exist; commit or revert first" >&2
  exit 1
fi

SETUP_COMMIT="$(git rev-parse HEAD)"
mkdir -p "${WORKTREE_ROOT}"

for route in "${ROUTES[@]}"; do
  path="${WORKTREE_ROOT}/${route}"

  if git show-ref --verify --quiet "refs/heads/${route}"; then
    branch_head="$(git rev-parse "${route}")"
    if [[ "${branch_head}" != "${SETUP_COMMIT}" ]]; then
      echo "ERROR: ${route} already exists at ${branch_head}, expected ${SETUP_COMMIT}" >&2
      exit 1
    fi
  else
    git branch "${route}" "${SETUP_COMMIT}"
  fi

  existing_path="$(git worktree list --porcelain | awk -v branch="refs/heads/${route}" '
    $1 == "worktree" { path=$2 }
    $1 == "branch" && $2 == branch { print path }
  ')"

  if [[ -n "${existing_path}" ]]; then
    if [[ "${existing_path}" != "${path}" ]]; then
      echo "ERROR: ${route} is already checked out at ${existing_path}" >&2
      exit 1
    fi
  elif [[ -e "${path}" ]]; then
    echo "ERROR: target path exists but is not the expected worktree: ${path}" >&2
    exit 1
  else
    git worktree add "${path}" "${route}"
  fi

  echo "route=${route}"
  echo "path=${path}"
  git -C "${path}" status --short
  git -C "${path}" rev-parse HEAD
  git -C "${path}" branch --show-current
done
