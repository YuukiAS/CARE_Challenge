#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-core}"
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
WORKTREE_ROOT="${WORKTREE_ROOT:-/users/a/e/aereinh/CARE_worktrees}"

create_session() {
  local name="$1"
  local cwd="$2"
  if tmux has-session -t "${name}" 2>/dev/null; then
    echo "EXISTS ${name}"
    return
  fi
  tmux new-session -d -s "${name}" -c "${cwd}"
  tmux send-keys -t "${name}" "source /users/a/e/aereinh/CARE/.care-codex-env.sh" C-m
  tmux send-keys -t "${name}" "source /users/a/e/aereinh/CARE/env_nnunet.sh" C-m
  tmux send-keys -t "${name}" "export PATH=/users/a/e/aereinh/codex-runtime/bin:/users/a/e/aereinh/CARE/envs/env_CARE/bin:\$PATH" C-m
  tmux send-keys -t "${name}" "git status --short" C-m
  tmux send-keys -t "${name}" "git branch --show-current" C-m
  tmux send-keys -t "${name}" "git rev-parse HEAD" C-m
  echo "CREATED ${name} cwd=${cwd}"
}

create_core() {
  create_session care_portfolio "${CARE_ROOT}"
  create_session care_route_A_controller "${WORKTREE_ROOT}/route_A"
  create_session care_route_B_controller "${WORKTREE_ROOT}/route_B"
  create_session care_route_C_controller "${WORKTREE_ROOT}/route_C"
}

create_reviewers() {
  create_session care_route_A_reviewer /users/a/e/aereinh/CARE_review_worktrees/route_A
  create_session care_route_B_reviewer /users/a/e/aereinh/CARE_review_worktrees/route_B
  create_session care_route_C_reviewer /users/a/e/aereinh/CARE_review_worktrees/route_C
}

case "${MODE}" in
  core) create_core ;;
  reviewers) create_reviewers ;;
  all) create_core; create_reviewers ;;
  *)
    echo "Usage: $0 {core|reviewers|all}" >&2
    exit 2
    ;;
esac
