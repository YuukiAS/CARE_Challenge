#!/bin/bash
# GPU 1: CineMyoPS 5-fold + full-data training
# Usage: nohup bash scripts/run_gpu1_cine.sh > logs/gpu1_cine.log 2>&1 &

set -e
cd "$(dirname "$0")/.."
mkdir -p logs

source ~/.bashrc
conda activate stai_tune

export CUDA_VISIBLE_DEVICES=1

echo "=== [$(date)] Starting CineMyoPS 5-fold CV ==="
python scripts/5fold_train_all.py \
    --data-dir "${DATA_DIR:?Set DATA_DIR to path of Myo_train}" \
    --mode cv \
    --tracks cine \
    --gpu 0

echo "=== [$(date)] CineMyoPS 5-fold CV complete ==="
# Full-data training launched separately in parallel
