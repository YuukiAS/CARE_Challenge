#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=B6FinalInt
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail
CARE_ROOT="${CARE_ROOT:-/users/a/e/aereinh/CARE}"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"
export PATH="/users/a/e/aereinh/codex-runtime/bin:${CARE_ROOT}/envs/env_CARE/bin:${PATH}"
mkdir -p logs/srr_batch6
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/srr_batch6/B6FinalInterventions_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

RESULT_ROOT="results/20260721_srr_batch6_final_objective_alignment"
CHECKPOINT="$(${CARE_ROOT}/envs/env_CARE/bin/python - <<'PYCHECK'
import json
obj=json.load(open('results/20260721_srr_batch6_final_objective_alignment/training_adequacy.json'))
if obj.get('continuation_gate_decision') not in {'PASS','FAIL'}:
    raise SystemExit('formal300 gate missing')
print(obj['selected_checkpoint_path'])
PYCHECK
)"
OUT_ROOT="${RESULT_ROOT}/final_interventions/step300"
CASES="$(${CARE_ROOT}/envs/env_CARE/bin/python - <<'PYCASES'
import json
print(','.join(sorted(json.load(open('data/benchmarks/protocol/splits_MyoPS.json'))['folds'][0]['val'])))
PYCASES
)"

echo "CHECKPOINT=${CHECKPOINT}"
echo "OUT_ROOT=${OUT_ROOT}"
"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PYTORCH'
import torch
print('torch', torch.__version__)
print('cuda_available', torch.cuda.is_available())
if not torch.cuda.is_available():
    raise SystemExit('CUDA_NOT_AVAILABLE_FOR_BATCH6_FINAL_INTERVENTIONS')
print('cuda_device_name', torch.cuda.get_device_name(0))
PYTORCH

for MODE in anchor_identity_control full_learned_gate full_gate_one full_gate_zero proposal_only_gate_one refiner_only_gate_one; do
  echo "running_mode=${MODE}"
  "${CARE_ROOT}/envs/env_CARE/bin/python" scripts/srr_production/infer_myops.py \
    --config configs/srr_production/myops_batch6.yaml \
    --mode "${MODE}" \
    --fold 0 \
    --cases "${CASES}" \
    --checkpoint "${CHECKPOINT}" \
    --training-summary "${RESULT_ROOT}/runtime/attempts/batch6_formal300_htzhulab_59744053/variants/batch6_formal300_htzhulab_59744053/summary.json" \
    --output-root "${OUT_ROOT}" \
    --device cuda
  echo "completed_mode=${MODE}"
done
