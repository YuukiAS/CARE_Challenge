#!/usr/bin/env bash
# Train MyoPS-Net (third_party/MyoPS-Net) on CARE-staged data under data/benchmarks/MyoPS-Net.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CARE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO="${CARE_ROOT}/third_party/MyoPS-Net"
FOLD="${FOLD:-0}"
DATA="${MYOPS_NET_DATA:-${CARE_ROOT}/data/benchmarks/MyoPS-Net/fold_${FOLD}}"
WORKDIR="${MYOPS_NET_WORKDIR:-${CARE_ROOT}/results/checkpoints/MyoPS-Net/fold_${FOLD}}"
PY="${CARE_ROOT}/envs/env_CARE/bin/python"
VARIANT="${MYOPS_NET_VARIANT:-challenge3}"
START_EPOCH="${MYOPS_NET_START_EPOCH:-}"
END_EPOCH="${MYOPS_NET_END_EPOCH:-}"
BATCH_SIZE="${MYOPS_NET_BATCH_SIZE:-}"
DIM="${MYOPS_NET_DIM:-}"
MAX_RUNTIME_HOURS="${MYOPS_NET_MAX_RUNTIME_HOURS:-}"
EARLY_STOP_PATIENCE="${MYOPS_NET_EARLY_STOP_PATIENCE:-}"
MASK_GATED_LOSS="${MYOPS_NET_MASK_GATED_LOSS:-}"
INIT_CHECKPOINT="${MYOPS_NET_INIT_CHECKPOINT:-}"
BEST_METRIC="${MYOPS_NET_BEST_METRIC:-}"
BEST_WEIGHT_SCAR="${MYOPS_NET_BEST_WEIGHT_SCAR:-}"
BEST_WEIGHT_EDEMA="${MYOPS_NET_BEST_WEIGHT_EDEMA:-}"

mkdir -p "${WORKDIR}"
cd "${WORKDIR}"
export PYTHONPATH="${REPO}:${PYTHONPATH:-}"
# Stdout: epoch-level logging (Slurm tee). Per-iteration loss still in log_training.txt and TensorBoard runs/.
echo "MyoPS-Net: repo=${REPO} | cwd=${WORKDIR} | variant=${VARIANT} | MYOPS_NET_END_EPOCH=${MYOPS_NET_END_EPOCH:-} | MYOPS_NET_MAX_RUNTIME_HOURS=${MYOPS_NET_MAX_RUNTIME_HOURS:-7.75} | MYOPS_NET_MASK_GATED_LOSS=${MYOPS_NET_MASK_GATED_LOSS:-0} | MYOPS_NET_INIT_CHECKPOINT=${MYOPS_NET_INIT_CHECKPOINT:-none} | MYOPS_NET_BEST_METRIC=${MYOPS_NET_BEST_METRIC:-avg_pathology} | MYOPS_NET_NUM_WORKERS=${MYOPS_NET_NUM_WORKERS:-4} | dense iter log: tail -f ${WORKDIR}/log_training.txt"
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
if [[ -n "${MAX_RUNTIME_HOURS}" ]]; then
  args+=( --max_runtime_hours "${MAX_RUNTIME_HOURS}" )
fi
if [[ -n "${EARLY_STOP_PATIENCE}" ]]; then
  args+=( --early_stop_patience "${EARLY_STOP_PATIENCE}" )
fi
if [[ "${MASK_GATED_LOSS}" =~ ^(1|true|TRUE|yes|YES|on|ON)$ ]]; then
  args+=( --mask_gated_loss )
fi
if [[ -n "${INIT_CHECKPOINT}" ]]; then
  args+=( --init_checkpoint "${INIT_CHECKPOINT}" )
fi
if [[ -n "${BEST_METRIC}" ]]; then
  args+=( --best_metric "${BEST_METRIC}" )
fi
if [[ -n "${BEST_WEIGHT_SCAR}" ]]; then
  args+=( --best_weight_scar "${BEST_WEIGHT_SCAR}" )
fi
if [[ -n "${BEST_WEIGHT_EDEMA}" ]]; then
  args+=( --best_weight_edema "${BEST_WEIGHT_EDEMA}" )
fi
exec "${PY}" -u "${REPO}/main.py" "${args[@]}" "$@"
