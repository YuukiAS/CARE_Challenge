#!/usr/bin/env bash
# Train MyoPS-Net (third_party/MyoPS-Net) on CARE-staged data under data/benchmarks/MyoPS-Net.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/MyoPS-Net"
FOLD="${FOLD:-0}"
DATA="${MYOPS_NET_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_${FOLD}}"
WORKDIR="${MYOPS_NET_WORKDIR:-${CARE_ROOT}/results/checkpoints/MyoPS-Net/fold_${FOLD}}"
PY="${CARE_ROOT}/env_CARE/bin/python"
VARIANT="${MYOPS_NET_VARIANT:-challenge3}"
START_EPOCH="${MYOPS_NET_START_EPOCH:-}"
END_EPOCH="${MYOPS_NET_END_EPOCH:-}"
BATCH_SIZE="${MYOPS_NET_BATCH_SIZE:-}"
DIM="${MYOPS_NET_DIM:-}"

mkdir -p "${WORKDIR}"
cd "${WORKDIR}"
export PYTHONPATH="${REPO}:${PYTHONPATH:-}"
# Stdout: epoch-level logging (Slurm tee). Per-iteration loss still in log_training.txt and TensorBoard runs/.
echo "MyoPS-Net: repo=${REPO} | cwd=${WORKDIR} | variant=${VARIANT} | dense iter log: tail -f ${WORKDIR}/log_training.txt"
args=( --path "${DATA}" --variant "${VARIANT}" )
if [[ -n "${START_EPOCH}" ]]; then
  args+=( --start_epoch "${START_EPOCH}" )
fi
if [[ -n "${END_EPOCH}" ]]; then
  args+=( --end_epoch "${END_EPOCH}" )
fi
if [[ -n "${BATCH_SIZE}" ]]; then
  args+=( --batch_size "${BATCH_SIZE}" )
fi
if [[ -n "${DIM}" ]]; then
  args+=( --dim "${DIM}" )
fi
exec "${PY}" -u "${REPO}/main.py" "${args[@]}" "$@"
