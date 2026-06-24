#!/usr/bin/env bash
set -euo pipefail

cd /overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval
export CODEX_HOME_OVERRIDE=/overflow/htzhu/mingcheng_new/.codex-home

/overflow/htzhu/mingcheng_new/bin/codex exec \
  --sandbox workspace-write \
  --add-dir /overflow/htzhu/CARE \
  -C /overflow/htzhu/mingcheng_new/temp/care_worktrees/20260621_cine_retrieval \
  - \
  < /overflow/htzhu/CARE/results/20260621_srr_goal/coordinator/cine_prompt.md \
  > /overflow/htzhu/CARE/results/20260621_srr_goal/coordinator/cine_tmux.log \
  2>&1
