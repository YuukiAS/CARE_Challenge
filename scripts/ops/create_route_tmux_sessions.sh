#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-core}"
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
WORKTREE_ROOT="${WORKTREE_ROOT:-/users/a/e/aereinh/CARE_worktrees}"

send_bootstrap() {
  local target="$1"
  tmux send-keys -t "${target}" "source /users/a/e/aereinh/CARE/.care-codex-env.sh" C-m
  tmux send-keys -t "${target}" "source /users/a/e/aereinh/CARE/env_nnunet.sh" C-m
  tmux send-keys -t "${target}" "export CARE_ROOT=\"\$(git rev-parse --show-toplevel)\"" C-m
  tmux send-keys -t "${target}" "export CODEX_REPO_ROOT=\"\$CARE_ROOT\"" C-m
  tmux send-keys -t "${target}" "export nnUNet_raw=\"\$CARE_ROOT/data/nnUNet/nnUNet_raw\"" C-m
  tmux send-keys -t "${target}" "export nnUNet_preprocessed=\"\$CARE_ROOT/data/nnUNet/nnUNet_preprocessed\"" C-m
  tmux send-keys -t "${target}" "export nnUNet_results=\"\$CARE_ROOT/data/nnUNet/nnUNet_results\"" C-m
  tmux send-keys -t "${target}" "export PATH=/users/a/e/aereinh/codex-runtime/bin:\"\$CARE_ROOT/envs/env_CARE/bin\":\$PATH" C-m
  tmux send-keys -t "${target}" "printf 'CARE_ROOT=%s\\nCODEX_REPO_ROOT=%s\\nCODEX_HOME=%s\\nTMPDIR=%s\\n' \"\$CARE_ROOT\" \"\$CODEX_REPO_ROOT\" \"\$CODEX_HOME\" \"\$TMPDIR\"" C-m
  tmux send-keys -t "${target}" "git status --short" C-m
  tmux send-keys -t "${target}" "git branch --show-current" C-m
  tmux send-keys -t "${target}" "git rev-parse HEAD" C-m
}

ensure_session() {
  local session="$1"
  local first_window="$2"
  local cwd="$3"
  if tmux has-session -t "${session}" 2>/dev/null; then
    echo "EXISTS ${session}"
    return
  fi
  tmux new-session -d -s "${session}" -n "${first_window}" -c "${cwd}"
  tmux set-window-option -t "${session}:${first_window}" allow-rename off >/dev/null
  send_bootstrap "${session}:${first_window}"
  echo "CREATED ${session}:${first_window} cwd=${cwd}"
}

ensure_window() {
  local session="$1"
  local window="$2"
  local cwd="$3"
  if tmux list-windows -t "${session}" -F '#{window_name}' 2>/dev/null | grep -Fxq "${window}"; then
    echo "EXISTS ${session}:${window}"
    return
  fi
  tmux new-window -d -t "${session}:" -n "${window}" -c "${cwd}"
  tmux set-window-option -t "${session}:${window}" allow-rename off >/dev/null
  send_bootstrap "${session}:${window}"
  echo "CREATED ${session}:${window} cwd=${cwd}"
}

ensure_route_session() {
  local route="$1"
  local label="$2"
  local cwd="${WORKTREE_ROOT}/${route}"
  local session="care_${route}"
  ensure_session "${session}" "${label}-Controller" "${cwd}"
  ensure_window "${session}" "${label}-Continue" "${cwd}"
  ensure_window "${session}" "${label}-Exec" "${cwd}"
  ensure_window "${session}" "${label}-Reviewer" "${cwd}"
}

create_core() {
  ensure_session care_watchboard bash "${CARE_ROOT}"
  ensure_window care_watchboard watchboard-tunnel "${CARE_ROOT}"
  ensure_route_session route_A RouteA
  ensure_route_session route_B RouteB
  ensure_route_session route_C RouteC
}

case "${MODE}" in
  core|all) create_core ;;
  reviewers)
    echo "Reviewer isolation now uses Route*-Reviewer windows inside care_route_A/B/C sessions. Run '$0 core' to ensure canonical windows." >&2
    ;;
  *)
    echo "Usage: $0 {core|reviewers|all}" >&2
    exit 2
    ;;
esac
