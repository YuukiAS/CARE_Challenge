#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 route_A|route_B|route_C" >&2
  exit 2
fi

ROUTE="$1"
case "${ROUTE}" in
  route_A|route_B|route_C) ;;
  *) echo "ERROR: unknown route ${ROUTE}" >&2; exit 2 ;;
esac

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
REVIEW_ROOT="${REVIEW_ROOT:-/users/a/e/aereinh/CARE_review_worktrees}"
COMMIT="${REVIEW_COMMIT:-}"

cd "${CARE_ROOT}"

if [[ -z "${COMMIT}" ]]; then
  COMMIT="$(git rev-parse "${ROUTE}")"
fi

path="${REVIEW_ROOT}/${ROUTE}"
if [[ -e "${path}" ]]; then
  echo "ERROR: reviewer worktree path already exists: ${path}" >&2
  exit 1
fi

mkdir -p "${REVIEW_ROOT}"
git worktree add --detach "${path}" "${COMMIT}"
git -C "${path}" status --short
git -C "${path}" rev-parse HEAD
