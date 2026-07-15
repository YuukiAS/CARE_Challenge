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
  tmux send-keys -t "${name}" "source \"\$(pwd)/env_nnunet.sh\"" C-m
  tmux send-keys -t "${name}" "export CARE_ROOT=\"\$(git rev-parse --show-toplevel)\"" C-m
  tmux send-keys -t "${name}" "export CODEX_REPO_ROOT=\"\$CARE_ROOT\"" C-m
  tmux send-keys -t "${name}" "export nnUNet_raw=\"\$CARE_ROOT/data/nnUNet/nnUNet_raw\"" C-m
  tmux send-keys -t "${name}" "export nnUNet_preprocessed=\"\$CARE_ROOT/data/nnUNet/nnUNet_preprocessed\"" C-m
  tmux send-keys -t "${name}" "export nnUNet_results=\"\$CARE_ROOT/data/nnUNet/nnUNet_results\"" C-m
  tmux send-keys -t "${name}" "export PATH=/users/a/e/aereinh/codex-runtime/bin:\"\$CARE_ROOT/envs/env_CARE/bin\":\$PATH" C-m
  tmux send-keys -t "${name}" "printf 'CARE_ROOT=%s\\nCODEX_REPO_ROOT=%s\\nCODEX_HOME=%s\\nTMPDIR=%s\\n' \"\$CARE_ROOT\" \"\$CODEX_REPO_ROOT\" \"\$CODEX_HOME\" \"\$TMPDIR\"" C-m
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
