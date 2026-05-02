#!/usr/bin/env bash
# Run unified offline evaluation for all currently supported benchmark models.
set -euo pipefail

CARE_ROOT="${CARE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
MODELS="${MODELS:-nnUNet501 MyoPS-Net nnUNet502 CineMyoPS}"
FOLDS="${FOLDS:-0 1 2 3 4}"

for MODEL in ${MODELS}; do
  echo "=== Unified eval: ${MODEL} (FOLDS=${FOLDS}) ==="
  bash "${CARE_ROOT}/scripts/evaluation/run_unified_eval_model.sh" "${MODEL}" --folds "${FOLDS}" "$@"
done
