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

mkdir -p "${WORKDIR}"
cd "${WORKDIR}"
export PYTHONPATH="${REPO}:${PYTHONPATH:-}"
# Stdout: epoch-level logging (Slurm tee). Per-iteration loss still in log_training.txt and TensorBoard runs/.
echo "MyoPS-Net: repo=${REPO} | cwd=${WORKDIR} | variant=${VARIANT} | dense iter log: tail -f ${WORKDIR}/log_training.txt"
exec "${PY}" -u "${REPO}/main.py" --path "${DATA}" --variant "${VARIANT}" "$@"
