#!/bin/bash
#SBATCH --job-name=care-watchboard-tunnel
#SBATCH --partition=general
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=10-00:00:00
#SBATCH --output=/users/a/e/aereinh/CARE/logs/watchboard_tunnel/care_watchboard_tunnel_%j.out

set -euo pipefail

CARE_ROOT=/users/a/e/aereinh/CARE
CLOUDFLARED=/users/a/e/aereinh/tunnel_cloudflared_backup/bin/cloudflared
CONFIG="${CARE_ROOT}/.tmp/cloudflared_watchboard/config.yml"
LOG_DIR="${CARE_ROOT}/logs/watchboard_tunnel"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/care_watchboard_tunnel_${SLURM_JOB_ID:-local}_${TS}.log}"

mkdir -p "${LOG_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE_ROOT=${CARE_ROOT}"
echo "CONFIG=${CONFIG}"
echo "LOG_FILE=${LOG_FILE}"
echo "HOSTNAME=watchboard.httpwwwcardiacnexus-ukb.com"
echo "SERVICE=http://127.0.0.1:8766"
date

exec "${CLOUDFLARED}" tunnel --config "${CONFIG}" run care-watchboard
