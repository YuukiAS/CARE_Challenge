#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="${CARE_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SESSION="${CARE_NOTIFY_TMUX_SESSION:-care_notifier}"
WINDOW="${CARE_NOTIFY_TMUX_WINDOW:-Notifier}"
POLL_SECONDS="${CARE_NOTIFY_POLL_SECONDS:-60}"
PYTHON="${CARE_NOTIFY_PYTHON:-${CARE_ROOT}/envs/env_CARE/bin/python}"
LOG_PATH="${CARE_NOTIFY_LOG_PATH:-${CARE_ROOT}/controller_notifications/logs/notify_goal_watcher.log}"
CODEX_RUNTIME_BIN_DIR="${CARE_CODEX_RUNTIME_BIN_DIR:-}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ "${1:-}" != "" ]]; then
  echo "usage: $0 [--dry-run]" >&2
  exit 2
fi

if [[ ! -x "${PYTHON}" ]]; then
  echo "missing executable python: ${PYTHON}" >&2
  exit 1
fi

window_exists() {
  tmux list-windows -t "${SESSION}" -F '#W' | grep -Fxq "${WINDOW}"
}

watcher_running() {
  ps -u "${USER:-$(id -un)}" -o cmd= \
    | grep -F "${CARE_ROOT}/controller_notifications/notify_goal_watcher.py" \
    | grep -F -- "--loop" \
    | grep -v grep >/dev/null 2>&1
}

WATCHER_INNER="cd '${CARE_ROOT}'; mkdir -p controller_notifications/logs controller_notifications/state; if [[ -f .care-codex-env.sh ]]; then source .care-codex-env.sh; fi; if [[ -f env_nnunet.sh ]]; then source env_nnunet.sh; fi; if [[ -n '${CODEX_RUNTIME_BIN_DIR}' ]]; then export PATH='${CODEX_RUNTIME_BIN_DIR}':'${CARE_ROOT}'/envs/env_CARE/bin:\$PATH; else export PATH='${CARE_ROOT}'/envs/env_CARE/bin:\$PATH; fi; exec >> '${LOG_PATH}' 2>&1; date -u +notify_goal_watcher_started_at_%Y-%m-%dT%H:%M:%SZ; exec '${PYTHON}' '${CARE_ROOT}/controller_notifications/notify_goal_watcher.py' --loop --poll-seconds '${POLL_SECONDS}'"
WATCHER_COMMAND=$(printf '%q ' bash -lc "${WATCHER_INNER}")

if tmux has-session -t "${SESSION}" 2>/dev/null; then
  if window_exists; then
    if watcher_running; then
      echo "watcher already running in existing window: ${SESSION}:${WINDOW}"
      exit 0
    fi
    if [[ "${DRY_RUN}" == "1" ]]; then
      echo "tmux respawn-window -k -t ${SESSION}:${WINDOW} ${WATCHER_COMMAND}"
      exit 0
    fi
    tmux respawn-window -k -t "${SESSION}:${WINDOW}" "${WATCHER_COMMAND}"
    echo "restarted ${SESSION}:${WINDOW}"
    exit 0
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "tmux new-window -t ${SESSION}: -n ${WINDOW} ${WATCHER_COMMAND}"
    exit 0
  fi
  tmux new-window -t "${SESSION}:" -n "${WINDOW}" "${WATCHER_COMMAND}"
  echo "started ${SESSION}:${WINDOW}"
  exit 0
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  echo "tmux new-session -d -s ${SESSION} -n ${WINDOW} ${WATCHER_COMMAND}"
  exit 0
fi

tmux new-session -d -s "${SESSION}" -n "${WINDOW}" "${WATCHER_COMMAND}"
echo "started ${SESSION}:${WINDOW}"
