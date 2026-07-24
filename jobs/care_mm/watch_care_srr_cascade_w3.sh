#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --job-name=SRRW3Watch
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=8G
#SBATCH --time=24:00:00
#SBATCH --partition=general

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/SRRW3Watch_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
export CARE_W3_WATCHER_ACTIVE=1

while true; do
  "${CARE_ROOT}/envs/env_CARE/bin/python" \
    scripts/evaluation/orchestrate_care_srr_cascade_w3.py \
    --once \
    --cache-monitor-only || true
  DECISION="$("${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
import json
from pathlib import Path
p=Path("results/20260724_care_myops_srr_cascade_submission_rescue/source_cache_race_state.json")
print(json.loads(p.read_text()).get("decision", "NEEDS_MONITOR") if p.exists() else "NEEDS_MONITOR")
PY
)"
  if [[ "${DECISION}" == "NEEDS_REPAIR" ]]; then
    exit 2
  fi
  sleep "${WATCH_INTERVAL_SECONDS:-7200}"
done
