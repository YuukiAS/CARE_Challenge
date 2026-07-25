# MoSAIC: Motion- and Supervision-Aware Inference for Myocardial Pathology Segmentation

Official implementation of **MoSAIC**, an anatomy-conditioned cascade for myocardial scar and edema segmentation from multi-sequence and cine cardiac magnetic resonance (CMR).

Developed for the [CARE-2026 CARE-Myocardium](https://care-challenge.github.io/) benchmark (220 MyoPS + 64 CineMyoPS cases, 7 centres).

## Overview

MoSAIC addresses two fundamental challenges in multi-centre myocardial pathology segmentation:

1. **Missing evidence** — sequences and labels vary across centres. Presence-gated encoding with a supervision-masked loss ensures that unannotated classes contribute zero gradient, allowing heterogeneous cohorts to be pooled without label noise.

2. **Absent intensity evidence** — in cine CMR, scar has no intensity signature. A motion-derived pathology head uses dense displacement fields anchored to end-diastole rather than image intensity, recasting an intensity problem as a kinematic one.

### Pipeline

```
Stage 1: CoarseNet (anatomy segmentation) → anatomy prior P, bounding box Ω
    ↓
Stage 2a: Scar Expert (multi-sequence, presence-gated fusion, SPG decoder)
Stage 2b: Edema Zone Expert (predicts edema ∪ scar, recovers edema by subtraction)
Stage 2c: Cine Motion Expert (motion field → pathology head, no intensity)
    ↓
Label Fusion: TTA → anatomy constraint → connected-component cleanup
```

## Installation

```bash
git clone https://github.com/<your-username>/MoSAIC.git
cd MoSAIC
pip install -r requirements.txt
```

Requires Python 3.9+ and PyTorch 2.0+.

## Data Preparation

This project uses the CARE-2026 CARE-Myocardium dataset. Organise the training data as:

```
Myo_train/
├── myops/
│   ├── Case1001/
│   │   ├── Case1001_DE.nii.gz      # LGE
│   │   ├── Case1001_C0.nii.gz      # bSSFP
│   │   ├── Case1001_T2.nii.gz      # T2 (if available)
│   │   └── Case1001_gd.nii.gz      # Ground truth
│   └── ...
└── cinemyops/
    ├── Case1001/
    │   ├── Case1001_SAX.nii.gz     # Cine SAX stack
    │   └── Case1001_gd.nii.gz      # Ground truth
    └── ...
```

## Training

### 5-Fold Cross-Validation

```bash
# MyoPS track (multi-sequence)
CUDA_VISIBLE_DEVICES=0 python scripts/5fold_train_all.py \
    --data-dir /path/to/Myo_train --tracks myops --gpu 0

# CineMyoPS track
CUDA_VISIBLE_DEVICES=1 python scripts/5fold_train_all.py \
    --data-dir /path/to/Myo_train --tracks cine --gpu 1
```

### Full-Data Training (for submission)

```bash
python scripts/train_full.py \
    --data-dir /path/to/Myo_train --tracks myops cine --gpu 0
```

## Inference

```bash
python scripts/infer_and_submit.py \
    --val-dir /path/to/Myo_val --gpu 0
```

This produces a submission ZIP in `outputs/` compatible with the CARE-2026 evaluation server.

## Docker Submission

Docker containers for the challenge are in `docker/`:

```bash
cd docker/myops
docker build -t mosaic-myops .
docker run --gpus all -v /path/to/input:/input -v /path/to/output:/output mosaic-myops

cd docker/cinemyops
docker build -t mosaic-cine .
docker run --gpus all -v /path/to/input:/input -v /path/to/output:/output mosaic-cine
```

Pre-trained weights should be placed in `docker/myops/weights/` and `docker/cinemyops/weights/` before building. See [Pre-trained Weights](#pre-trained-weights).

## Pre-trained Weights

Pre-trained model weights can be downloaded from: **[TBD — link to be added]**

Place the downloaded files as:

```
docker/myops/weights/
├── coarse.pt
├── coarse_edema.pt
├── fine_scar.pt
└── edema.pt

docker/cinemyops/weights/
├── coarse.pt
├── fine_v1.pt
└── fine_v2.pt
```

## Project Structure

```
MoSAIC/
├── myops/                  # Main Python package
│   ├── data/               # Dataset, preprocessing, transforms
│   ├── engine/             # Training loop, losses
│   ├── inference/          # Prediction, postprocessing
│   ├── models/             # Network architectures
│   └── utils/              # Metrics, I/O helpers
├── configs/                # Training YAML configs
├── scripts/                # Training, evaluation, inference scripts
├── docker/                 # Docker submission containers
├── requirements.txt
└── LICENSE
```

## Citation

```bibtex
@inproceedings{mosaic2026,
  title     = {{MoSAIC}: Motion- and Supervision-Aware Inference for
               Myocardial Pathology Segmentation from
               Multi-Sequence and Cine {CMR}},
  author    = {Anonymous},
  booktitle = {CARE-2026 CARE-Myocardium Challenge},
  year      = {2026}
}
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
