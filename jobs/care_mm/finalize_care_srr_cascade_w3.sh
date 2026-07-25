#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --job-name=SRRW3Final
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=8G
#SBATCH --time=1:00:00
#SBATCH --partition=general

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/SRRW3Final_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

RESULT_ROOT="${CARE_ROOT}/results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT="${RESULT_ROOT}/runtime_closure_repair_rc1"
RECEIPT="${RC1_ROOT}/preformal_gate_finalizer_${SLURM_JOB_ID:-local}_${TS}.json"

set +e
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/run_care_srr_cascade_rc2_preflight.py --gate
GATE_EXIT=$?
set -e

GATE_DECISION="$("${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import json
from pathlib import Path
p = Path("results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/formal_authorization_gate.json")
print(json.loads(p.read_text()).get("decision", "MISSING") if p.exists() else "MISSING")
PY
)"

ORCHESTRATOR_EXIT="NOT_RUN"
FORMAL_SUBMIT_MODE="${CARE_SRR_ALLOW_FORMAL_SUBMIT:-0}"
if [[ "${GATE_DECISION}" == "PASS" && "${FORMAL_SUBMIT_MODE}" == "1" ]]; then
  set +e
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/orchestrate_care_srr_cascade_w3.py --submit
  ORCHESTRATOR_EXIT=$?
  set -e
elif [[ "${GATE_DECISION}" == "PASS" ]]; then
  set +e
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/orchestrate_care_srr_cascade_w3.py
  ORCHESTRATOR_EXIT=$?
  set -e
fi

set +e
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/finalize_care_srr_cascade_w3_accounting.py \
  --finalizer-job-id "${SLURM_JOB_ID:-local}" \
  --dependency-job-ids "${CARE_SRR_PREFLIGHT_DEPENDENCY_JOB_ID:-unknown}" \
  --log-file "${LOG_FILE}"
ACCOUNTING_EXIT=$?
set -e

set +e
"${CARE_ROOT}/envs/env_CARE/bin/python" scripts/evaluation/aggregate_care_srr_cascade_w4.py
AGGREGATION_EXIT=$?
set -e

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<PY
import json
from pathlib import Path

receipt = {
    "schema_version": 1,
    "slurm_job_id": "${SLURM_JOB_ID:-local}",
    "dependency_job_id": "${CARE_SRR_PREFLIGHT_DEPENDENCY_JOB_ID:-unknown}",
    "gate_exit_code": ${GATE_EXIT},
    "gate_decision": "${GATE_DECISION}",
    "formal_submit_mode": "${FORMAL_SUBMIT_MODE}",
    "formal_submit_attempted": "${FORMAL_SUBMIT_MODE}" == "1" and "${GATE_DECISION}" == "PASS",
    "orchestrator_exit": "${ORCHESTRATOR_EXIT}",
    "terminal_accounting_exit": ${ACCOUNTING_EXIT},
    "terminal_accounting_path": "results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/formal_terminal_accounting_v2.json",
    "w4_aggregation_exit": ${AGGREGATION_EXIT},
    "w4_aggregation_path": "results/20260724_care_myops_srr_cascade_submission_rescue/runtime_closure_repair_rc1/w4_aggregation_status_v2.json",
    "log_file": "${LOG_FILE}",
}
path = Path("${RECEIPT}")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
PY

if [[ "${GATE_DECISION}" != "PASS" ]]; then
  exit "${GATE_EXIT}"
fi
if [[ "${ORCHESTRATOR_EXIT}" != "NOT_RUN" && "${ORCHESTRATOR_EXIT}" != "0" ]]; then
  exit "${ORCHESTRATOR_EXIT}"
fi
if [[ "${ACCOUNTING_EXIT}" != "0" ]]; then
  exit "${ACCOUNTING_EXIT}"
fi
if [[ "${AGGREGATION_EXIT}" != "0" ]]; then
  exit "${AGGREGATION_EXIT}"
fi
