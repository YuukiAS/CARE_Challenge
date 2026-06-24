#!/usr/bin/env bash
set -euo pipefail

cd /overflow/htzhu/CARE
export CODEX_HOME_OVERRIDE=/overflow/htzhu/mingcheng_new/.codex-home

/overflow/htzhu/mingcheng_new/bin/codex exec \
  --sandbox workspace-write \
  --add-dir /overflow/htzhu/mingcheng_new/temp \
  -C /overflow/htzhu/CARE \
  - \
  < /overflow/htzhu/CARE/results/20260621_srr_goal/coordinator/main_goal_prompt.md \
  > /overflow/htzhu/CARE/results/20260621_srr_goal/coordinator/main_goal_tmux.log \
  2>&1
