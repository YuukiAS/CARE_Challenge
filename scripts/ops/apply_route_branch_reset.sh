#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
APPLY="${CARE_APPLY_REMOTE_BRANCH_RESET:-0}"

cd "${CARE_ROOT}"

EXPECTED_ORIGIN_MAIN="91e7af36bbb6b9ecef13a43b83277f25433b4e60"
EXPECTED_DELETED_BRANCHES=(
  agent/m10-deadline-myops-rescue-planner-draft
  agent/m10-followup-planner-draft
  agent/m10-followup-planning-critic-repair
  agent/m10-followup2-planner-draft
  agent/m10-followup2-planning-critic-repair
  agent/m10-planner-draft
  agent/m10-planning-critic-repair
  autopilot-closed-loop
)

echo "Fetching and checking remote state"
git fetch --all --prune

origin_main="$(git rev-parse origin/main)"
if [[ "${origin_main}" != "${EXPECTED_ORIGIN_MAIN}" ]]; then
  echo "ERROR: origin/main drifted: ${origin_main}, expected ${EXPECTED_ORIGIN_MAIN}" >&2
  exit 1
fi

for branch in "${EXPECTED_DELETED_BRANCHES[@]}"; do
  if git show-ref --verify --quiet "refs/remotes/origin/${branch}"; then
    echo "REMOTE_STILL_PRESENT ${branch}"
  else
    echo "REMOTE_ALREADY_ABSENT ${branch}"
  fi
done

commands=(
  "git push origin main"
  "git push origin route_A"
  "git push origin route_B"
  "git push origin route_C"
)

if [[ "${APPLY}" != "1" ]]; then
  printf 'DRY-RUN %s\n' "${commands[@]}"
  echo "Set CARE_APPLY_REMOTE_BRANCH_RESET=1 to push main and route branches."
  exit 0
fi

for cmd in "${commands[@]}"; do
  echo "RUN ${cmd}"
  ${cmd}
done

git fetch --all --prune
git branch -r
