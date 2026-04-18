#!/usr/bin/env bash
# Train MyoPS-Net (third_party/MyoPS-Net) on CARE-staged data under data/benchmarks/MyoPS-Net.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/MyoPS-Net"
DATA="${MYOPS_NET_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net}"
PY="${CARE_ROOT}/env_CARE/bin/python"

cd "${REPO}"
# Stdout: epoch-level logging (Slurm tee). Per-iteration loss still in log_training.txt and TensorBoard runs/.
echo "MyoPS-Net: cwd=${REPO} | dense iter log: tail -f log_training.txt"
exec "${PY}" -u main.py --path "${DATA}" "$@"
