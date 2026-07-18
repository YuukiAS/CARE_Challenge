#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
WORKTREE_ROOT="${WORKTREE_ROOT:-/users/a/e/aereinh/CARE_worktrees}"
ROUTES=(route_A route_B route_C)
LEGACY_SESSIONS=(
  care_portfolio
  care_route_A_controller
  care_route_B_controller
  care_route_C_controller
  care_route_A_reviewer
  care_route_B_reviewer
  care_route_C_reviewer
)

cd "${CARE_ROOT}"

echo "main_sha=$(git rev-parse main)"
echo "origin_main_sha=$(git rev-parse origin/main 2>/dev/null || true)"
echo

for route in "${ROUTES[@]}"; do
  echo "== ${route} =="
  if git show-ref --verify --quiet "refs/heads/${route}"; then
    echo "sha=$(git rev-parse "${route}")"
    echo "ahead_behind_main=$(git rev-list --left-right --count main...${route})"
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

session_present() {
  local session="$1"
  tmux has-session -t "${session}" 2>/dev/null
}

window_present() {
  local session="$1"
  local window="$2"
  tmux list-windows -t "${session}" -F '#{window_name}' 2>/dev/null | grep -Fxq "${window}"
}

print_session() {
  local session="$1"
  if session_present "${session}"; then
    echo "${session}=present"
  else
    echo "${session}=missing"
  fi
}

print_window() {
  local session="$1"
  local window="$2"
  if window_present "${session}" "${window}"; then
    echo "${session}:${window}=present"
  else
    echo "${session}:${window}=missing"
  fi
}

watchboard_service_present() {
  local rows
  rows="$(tmux list-windows -t care_watchboard -F '#{window_name}|#{pane_current_command}' 2>/dev/null || true)"
  awk -F'|' '$1 == "bash" || $1 ~ /python/ || $2 == "bash" || $2 ~ /python/ { found=1 } END { exit !found }' <<<"${rows}"
}

print_watchboard_service_window() {
  if watchboard_service_present; then
    echo "care_watchboard:bash_or_service=present"
  else
    echo "care_watchboard:bash_or_service=missing"
  fi
}

echo "== canonical tmux =="
print_session care_watchboard
print_watchboard_service_window || true
print_window care_watchboard watchboard-tunnel || true
for label in A B C; do
  session="care_route_${label}"
  print_session "${session}"
  print_window "${session}" "Route${label}-Controller" || true
  print_window "${session}" "Route${label}-Continue" || true
  print_window "${session}" "Route${label}-Exec" || true
  print_window "${session}" "Route${label}-Reviewer" || true
done

echo
echo "== legacy aliases present only =="
for session in "${LEGACY_SESSIONS[@]}"; do
  if session_present "${session}"; then
    echo "${session}=present"
  fi
done

echo
echo "== Slurm route jobs =="
squeue -h -o '%i|%P|%T|%j' 2>/dev/null | awk -F'|' '/route_A|route_B|route_C/ {print}' || true

echo
echo "== Partition summary =="
sinfo -o '%P|%a|%l|%D|%t|%G' 2>/dev/null | awk -F'|' '/htzhulab|a100-gpu|volta-gpu/ {print}' || true
