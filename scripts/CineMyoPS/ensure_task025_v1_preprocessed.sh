#!/usr/bin/env bash
# Ensure Task025 (CineMyoPS paper) nnU-Net v1 raw + plan_and_preprocess exist under env_nnunet.sh paths.
# Uses env_CARE_nnUNet_v1 Python + bundled nnunet under third_party/CineMyoPS/code.
#
# Env: CARE_ROOT (required), CINE_NNUNET_TASK (default Task025_Cine_Seg),
#      CARE_CONDA_ENV_NNUNET_V1, CINE_NNUNET_PL / CINE_NNUNET_PF (thread counts),
#      CINE_SKIP_V1_PREPROCESS=1 to skip, CINE_FORCE_PREPROCESS=1 to redo preprocessing.
set -euo pipefail

: "${CARE_ROOT:?CARE_ROOT must be set}"
# shellcheck source=/dev/null
source "${CARE_ROOT}/env_nnunet.sh"

TASK="${CINE_NNUNET_TASK:-Task025_Cine_Seg}"
V1_ENV="${CARE_CONDA_ENV_NNUNET_V1:-${CARE_ROOT}/env_CARE_nnUNet_v1}"
PY="${V1_ENV}/bin/python"
REPO="${CARE_ROOT}/third_party/CineMyoPS/code"
PP="${REPO}/nnunet/experiment_planning/old/old_plan_and_preprocess_task.py"
PL="${CINE_NNUNET_PL:-8}"
PF="${CINE_NNUNET_PF:-8}"

if [[ "${CINE_SKIP_V1_PREPROCESS:-0}" == "1" ]]; then
  echo "=== Skip Task025 v1 preprocess (CINE_SKIP_V1_PREPROCESS=1) ==="
  exit 0
fi

if [[ ! -x "${PY}" ]]; then
  echo "error: v1 python not found: ${PY}" >&2
  exit 1
fi
if [[ ! -f "${PP}" ]]; then
  echo "error: missing ${PP}" >&2
  exit 1
fi

raw_task="${nnUNet_raw}/${TASK}"
if [[ ! -f "${raw_task}/dataset.json" ]]; then
  echo "=== Prepare Task025 raw -> ${raw_task} ==="
  "${PY}" "${CARE_ROOT}/scripts/CineMyoPS/prepare_task025_from_care.py" --output "${raw_task}"
fi
# nnU-Net v1 expects training "image": ./imagesTr/{case}.nii.gz (not .../{case}_0000.nii.gz) or crop looks for *_0000_0000.nii.gz.
if ! "${PY}" -c "
import json, sys
p = sys.argv[1]
d = json.load(open(p))
for t in d.get('training', []):
    img = t.get('image', '').split('/')[-1].removesuffix('.nii.gz')
    if img.endswith('_0000'):
        sys.exit(1)
sys.exit(0)
" "${raw_task}/dataset.json"; then
  _crop_root="${nnUNet_cropped_data:-$(dirname "${nnUNet_raw}")/nnUNet_cropped_data}"
  echo "error: ${raw_task}/dataset.json uses legacy image paths (*_0000.nii.gz). nnU-Net v1 needs ./imagesTr/{case_id}.nii.gz." >&2
  echo "  Fix: rm -rf \"${raw_task}\" \"${_crop_root}/${TASK}\" \"${nnUNet_preprocessed}/${TASK}\" then re-run this script." >&2
  exit 1
fi

plans="${nnUNet_preprocessed}/${TASK}/nnUNetPlansv2.1_plans_2D.pkl"
legacy="${nnUNet_preprocessed}/${TASK}/nnUNetPlans_plans_2D.pkl"
if [[ ! -f "${plans}" && -f "${legacy}" ]]; then
  ln -sf "nnUNetPlans_plans_2D.pkl" "${plans}"
  echo "=== Linked ${plans} -> nnUNetPlans_plans_2D.pkl (old planner output name) ==="
fi
if [[ -f "${plans}" && "${CINE_FORCE_PREPROCESS:-0}" != "1" ]]; then
  echo "=== Task025 v1 preprocess already present: ${plans} ==="
  exit 0
fi

echo "=== nnU-Net v1 plan+preprocess -t ${TASK} (nnUNet_preprocessed=${nnUNet_preprocessed}) ==="
export PYTHONPATH="${REPO}:${PYTHONPATH:-}"
"${PY}" "${PP}" -t "${TASK}" -pl "${PL}" -pf "${PF}"

# old_plan_and_preprocess uses ExperimentPlanner2D -> nnUNetPlans_plans_2D.pkl, but training
# (default_plans_identifier=nnUNetPlansv2.1) expects nnUNetPlansv2.1_plans_2D.pkl. Same pickle content.
ppdir="${nnUNet_preprocessed}/${TASK}"
if [[ -f "${ppdir}/nnUNetPlans_plans_2D.pkl" && ! -f "${ppdir}/nnUNetPlansv2.1_plans_2D.pkl" ]]; then
  ln -sf "nnUNetPlans_plans_2D.pkl" "${ppdir}/nnUNetPlansv2.1_plans_2D.pkl"
  echo "Linked ${ppdir}/nnUNetPlansv2.1_plans_2D.pkl -> nnUNetPlans_plans_2D.pkl"
fi
