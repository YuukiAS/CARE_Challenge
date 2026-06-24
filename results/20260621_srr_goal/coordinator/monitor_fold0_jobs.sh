#!/usr/bin/env bash
set -uo pipefail

CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"
cd "${CARE_ROOT}" || exit 1

JOB_IDS="${JOB_IDS:-55723114,55723115}"
POLL_SECONDS="${POLL_SECONDS:-600}"
MONITOR_LOG="${MONITOR_LOG:-${CARE_ROOT}/results/20260621_srr_goal/coordinator/monitor_fold0_jobs.log}"

mkdir -p "$(dirname "${MONITOR_LOG}")"
exec > >(tee -a "${MONITOR_LOG}") 2>&1

echo "monitor_start=$(date '+%Y-%m-%d %H:%M:%S')"
echo "JOB_IDS=${JOB_IDS}"

while true; do
  echo
  echo "poll=$(date '+%Y-%m-%d %H:%M:%S')"
  squeue -j "${JOB_IDS}" -o '%.18i %.24j %.2t %.10M %.20R'
  active_count="$(squeue -h -j "${JOB_IDS}" 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${active_count}" == "0" ]]; then
    break
  fi
  sleep "${POLL_SECONDS}"
done

echo
echo "final_sacct=$(date '+%Y-%m-%d %H:%M:%S')"
sacct -j "${JOB_IDS}" --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS,AllocTRES%50 -P

echo
echo "running_fold0_report=$(date '+%Y-%m-%d %H:%M:%S')"
if ./envs/env_CARE/bin/python scripts/evaluation/report_srr_fold0.py --root results/20260621_srr_fold0; then
  report_status="OK"
else
  report_status="FAILED"
fi

{
  echo
  echo "- \`$(date '+%Y-%m-%d %H:%M')\` monitor: jobs \`${JOB_IDS}\` finished; report_srr_fold0.py status \`${report_status}\`. See \`${MONITOR_LOG}\`."
} >> results/20260621_srr_goal/progress.md

echo "monitor_done=$(date '+%Y-%m-%d %H:%M:%S') report_status=${report_status}"
