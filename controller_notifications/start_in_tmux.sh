#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
SESSION="${CARE_NOTIFY_TMUX_SESSION:-care_watchboard}"
WINDOW="${CARE_NOTIFY_TMUX_WINDOW:-Notify}"
POLL_SECONDS="${CARE_NOTIFY_POLL_SECONDS:-60}"
PYTHON="${CARE_NOTIFY_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
LOG_PATH="${CARE_NOTIFY_LOG_PATH:-${CARE_ROOT}/controller_notifications/logs/notify_goal_watcher.log}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

if ! tmux has-session -t "${SESSION}" 2>/dev/null; then
  echo "missing tmux session: ${SESSION}" >&2
  echo "start the CARE watchboard session first; this script will not create a new ops session" >&2
  exit 1
fi

if tmux list-windows -t "${SESSION}" -F '#W' | grep -Fxq "${WINDOW}"; then
  echo "tmux window already exists: ${SESSION}:${WINDOW}"
  exit 0
fi

COMMAND=$(printf '%q ' bash -lc "cd '${CARE_ROOT}'; mkdir -p controller_notifications/logs controller_notifications/state; if [[ -f .care-codex-env.sh ]]; then source .care-codex-env.sh; fi; if [[ -f env_nnunet.sh ]]; then source env_nnunet.sh; fi; export PATH=/users/a/e/aereinh/codex-runtime/bin:'${CARE_ROOT}'/envs/env_CARE/bin:\$PATH; exec >> '${LOG_PATH}' 2>&1; echo \"notify_goal_watcher started at \$(date -u +%Y-%m-%dT%H:%M:%SZ)\"; '${PYTHON}' controller_notifications/notify_goal_watcher.py --loop --poll-seconds '${POLL_SECONDS}'")

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "tmux new-window -t ${SESSION}: -n ${WINDOW} ${COMMAND}"
  exit 0
fi

tmux new-window -t "${SESSION}:" -n "${WINDOW}" "${COMMAND}"
echo "started ${SESSION}:${WINDOW}"
