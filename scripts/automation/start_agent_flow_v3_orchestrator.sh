#!/usr/bin/env bash
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-${CARE_ROOT}/envs/env_CARE/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-/users/a/e/aereinh/CARE/envs/env_CARE/bin/python}"
fi

exec "${PYTHON_BIN}" "${CARE_ROOT}/scripts/automation/agent_flow_v3_runtime.py" \
  start-stage-orchestrator \
  --repo-root "${CARE_ROOT}" \
  --branch "${CARE_AGENT_FLOW_BRANCH:-develop}" \
  --state-root "${CARE_AGENT_FLOW_ORCHESTRATOR_STATE_ROOT:-/users/a/e/aereinh/.agent-flow-v3/stage_orchestrator}" \
  --poll-seconds "${CARE_AGENT_FLOW_ORCHESTRATOR_POLL_SECONDS:-60}" \
  --default-wait-hours "${CARE_AGENT_FLOW_EXTERNAL_WAIT_HOURS:-4}" \
  --output "${CARE_AGENT_FLOW_ORCHESTRATOR_RECEIPT:-/users/a/e/aereinh/.agent-flow-v3/stage_orchestrator/stage_orchestrator_receipt.json}"
