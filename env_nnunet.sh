#!/usr/bin/env bash
# Source from repo root:  source env_nnunet.sh
# Or use conda activate env_CARE — see env_CARE/etc/conda/activate.d/care_nnunet_env.sh
# Adjust CARE_ROOT if you relocate the project.

export CARE_ROOT="${CARE_ROOT:-/overflow/htzhu/CARE}"

# All transient data (tmp, torch/triton, pip, XDG cache, etc.) under project temp/ — not $HOME (quota).
# See .gitignore: temp/
export CARE_TEMP="${CARE_TEMP:-$CARE_ROOT/temp}"
export TMPDIR="${TMPDIR:-$CARE_TEMP/tmp}"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$CARE_TEMP/xdg_cache}"

export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-$CARE_TEMP/triton}"
export TORCHINDUCTOR_CACHE_DIR="${TORCHINDUCTOR_CACHE_DIR:-$CARE_TEMP/torch_inductor}"
export TORCH_HOME="${TORCH_HOME:-$CARE_TEMP/torch}"

export HF_HOME="${HF_HOME:-$CARE_TEMP/huggingface}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$CARE_TEMP/huggingface/datasets}"

export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$CARE_TEMP/pip}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$CARE_TEMP/matplotlib}"
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-$CARE_TEMP/numba}"

export nnUNet_raw="${nnUNet_raw:-$CARE_ROOT/data/nnUNet/nnUNet_raw}"
export nnUNet_preprocessed="${nnUNet_preprocessed:-$CARE_ROOT/data/nnUNet/nnUNet_preprocessed}"
export nnUNet_results="${nnUNet_results:-$CARE_ROOT/data/nnUNet/nnUNet_results}"

mkdir -p "$nnUNet_raw" "$nnUNet_preprocessed" "$nnUNet_results" \
  "$TMPDIR" "$XDG_CACHE_HOME" \
  "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$TORCH_HOME" \
  "$HF_HOME" "$HF_DATASETS_CACHE" \
  "$PIP_CACHE_DIR" "$MPLCONFIGDIR" "$NUMBA_CACHE_DIR"

# Optional: activate conda env (uncomment and edit if needed)
# source "$(conda info --base)/etc/profile.d/conda.sh"
# conda activate /overflow/htzhu/CARE/env_CARE

export PATH="${CARE_ROOT}/env_CARE/bin:${PATH}"

if [[ "${NNUNET_ENV_SILENT:-}" != "1" ]]; then
  echo "nnUNet_raw=$nnUNet_raw"
  echo "nnUNet_preprocessed=$nnUNet_preprocessed"
  echo "nnUNet_results=$nnUNet_results"
  echo "CARE_TEMP=$CARE_TEMP TMPDIR=$TMPDIR"
fi

# CARE challenge source (raw NIfTI); conversion scripts default here
export CARE_CHALLENGE_ROOT="${CARE_CHALLENGE_ROOT:-$CARE_ROOT/data/CARE_Challenge}"
