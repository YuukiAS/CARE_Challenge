#!/bin/bash
# GPU 0: MyoPS 5-fold + full-data training
# Usage: nohup bash scripts/run_gpu0_myops.sh > logs/gpu0_myops.log 2>&1 &

set -e
cd "$(dirname "$0")/.."
mkdir -p logs

source ~/.bashrc
conda activate stai_tune

export CUDA_VISIBLE_DEVICES=0

echo "=== [$(date)] Starting MyoPS 5-fold CV ==="
python scripts/5fold_train_all.py \
    --data-dir "${DATA_DIR:?Set DATA_DIR to path of Myo_train}" \
    --mode cv \
    --tracks myops \
    --gpu 0

echo "=== [$(date)] MyoPS 5-fold CV complete ==="
# Full-data training launched separately in parallel
