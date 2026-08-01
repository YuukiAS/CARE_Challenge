# External Assets And Download Plan

本文件记录四模型缺口闭合任务的外部源码和资产位置。它不是训练完成证明；训练和正式评价仍需后续 job terminal accounting。

## M0R_FAITHFUL_CONTROL

- 外部源码：无。使用本仓库 `nnUNetTrainerGapClosureM0R4000` 和本地 Dataset501 nnU-Net plans/checkpoints。
- 关键本地资产：
  - `data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json`
  - `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_2/checkpoint_final.pth`
  - `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_3/checkpoint_final.pth`
- 已验证：fold2/fold3 stock parity PASS；optimizer contract 为 AdamW，非 SGD/PolyLR。

## M1_MYOPSNET_L_CARE

- 官方源码：`https://github.com/QJYBall/MyoPS-Net.git`
- 合同 commit：`479f07028c5bdb12b405dc92212aa48ae6ba947a`
- 本地 pinned checkout：`third_party/MyoPS-Net_PINNED`
- 当前本地命令：

```bash
git clone https://github.com/QJYBall/MyoPS-Net.git third_party/MyoPS-Net_PINNED
git -C third_party/MyoPS-Net_PINNED checkout 479f07028c5bdb12b405dc92212aa48ae6ba947a
```

- 上游 README 数据组织要求：`data/train_set/train_image`, `data/train_set/train_gd`, `data/val_set`, `data/test_set`，并用 `train.txt`, `validation.txt`, `test.csv` 索引。
- CARE 适配方案：不要使用上游 private/public MyoPS 数据训练；从 Dataset501 complete tri-modal `[LGE,T2,C0]` 导出 slice records，构造 C0/LGE/T2-only forward，按 `scar=5`, `pure_edema=4`, `injury=4|5` 生成 full-volume reconstruction。
- 当前 preflight：pinned source 到位；本地 C0/LGE/T2-only forward smoke PASS；还需要正式 CARE full-volume exporter 和 >=60 epoch training job。

## M2_I_MMSEG_CARE

- 官方源码：`https://github.com/zzzzzzl24/I_MMSeg.git`
- 合同 commit：`90f46c4eb72924509895fcda6bc6a3b8c3316e66`
- 本地 pinned checkout：`third_party/I_MMSeg_PINNED`
- 当前本地命令：

```bash
git clone https://github.com/zzzzzzl24/I_MMSeg.git third_party/I_MMSeg_PINNED
git -C third_party/I_MMSeg_PINNED checkout 90f46c4eb72924509895fcda6bc6a3b8c3316e66
```

- 上游 Google Drive folder：`https://drive.google.com/drive/folders/1WHcpG8YlDlEdnlclbXKDZJANLX10iSq3?usp=drive_link`
- 上游 README 列出的包：
  - `I_MMSeg_env.tar.gz`
  - `R50-ViT-B_16.npz`
  - `epoch_299.pth`
  - `MyoPS380 dataset (raw + processed; available upon approval)`
- 预期放置路径：
  - `third_party/I_MMSeg_PINNED/model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz`
  - `third_party/I_MMSeg_PINNED/weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth`
  - `third_party/I_MMSeg_PINNED/text_features/embedding_class_information.pth` 已随源码存在
  - `third_party/I_MMSeg_PINNED/text_features/embedding_MRI_information.pth` 已随源码存在
- 2026-08-01 实测：Google Drive folder 可公开列目录。`gdown --folder --json` 返回了公开 file id；本次只下载两个模型资产，没有下载 `MyoPS380_dataset/` 或 `I_MMSeg_env.tar.gz`。

已下载并放置：

```text
R50-ViT-B_16.npz
source: https://drive.google.com/uc?id=1qJI7m6sM6deBZsSmcZjltHNWygRYagdD
path: third_party/I_MMSeg_PINNED/model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz
size_bytes: 461217452
sha256: ff009bf39bb4f9198b834cfe46aba2bfdaf730e933ab3e3c4b1edf4226eaafbe

epoch_299.pth
source: https://drive.google.com/uc?id=1niuQ5BDD1A4lX3oN-ARZ0f3NO1GxLu6F
path: third_party/I_MMSeg_PINNED/weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth
size_bytes: 340373498
sha256: 56a274d79638ba3dc5a44b5243e3e339702e3ec46ce0714fc2acfb1ab0835da6
```

可复现下载命令：

```bash
./envs/env_CARE/bin/python -m pip install gdown
mkdir -p third_party/I_MMSeg_PINNED/model/vit_checkpoint/imagenet21k
mkdir -p third_party/I_MMSeg_PINNED/weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128
./envs/env_CARE/bin/python -m gdown \
  'https://drive.google.com/uc?id=1qJI7m6sM6deBZsSmcZjltHNWygRYagdD' \
  -O third_party/I_MMSeg_PINNED/model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz \
  --continue
./envs/env_CARE/bin/python -m gdown \
  'https://drive.google.com/uc?id=1niuQ5BDD1A4lX3oN-ARZ0f3NO1GxLu6F' \
  -O third_party/I_MMSeg_PINNED/weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth \
  --continue
```

- BiomedCLIP 运行时资产：`train.py` 调用 `open_clip.create_model_from_pretrained('hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224')`，首次运行需要 HuggingFace 网络/缓存或预先下载缓存。
- MyoPS380 边界：上游文档说 release agreement 需签名并从机构邮箱发送给 `donggenf@whu.edu.cn`，主题 `MyoPS380 Dataset Release Agreement`。CARE 本任务不应下载或混用 MyoPS380 作为训练数据；M2 只允许用官方 I-MMSeg 结构和公开/获批的模型资产适配 Dataset501。
- 当前 preflight：pinned source 到位，CLIP/text prior code signal 到位，rank-channel substitute 未使用；Google Drive ViT/checkpoint 核心资产已放置。Dataset501 CARE adapter preflight 已通过，receipt 见 `results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/adapter_preflight_report.json`；MyoPS380 数据集仍不得混用。
- 2026-08-01 GPU smoke：在 existing `61220581 / htzhulab / NVIDIA H100 NVL` 上，released `epoch_299.pth` 以 `strict=False` 后 missing/unexpected keys 均为 0，三路 1x128x128 forward 输出 `(1,4,128,128)` 且 finite，receipt 见 `results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/released_checkpoint_smoke_receipt.json`。
- 上游 fidelity 风险：`VisionTransformer.load_from(R50-ViT-B_16.npz)` 当前 release 会失败，因为该 legacy 方法引用 `self.transformer`，而模型实际定义 `transformer1/transformer2/transformer3`。上游 `train.py/test.py` 也没有调用该方法；当前可用路径是加载 released `epoch_299.pth`。如果 planner 要求从 ViT npz 初始化再 CARE train，需要先修复三编码器 load_from 语义。
- 2026-08-01 formal job：M2 fold2/fold3 lane job `61627615` 已在 `htzhulab / g1807htzh01` `COMPLETED 0:0`，elapsed `00:24:56`；log 为 `logs/M2IMM_61627615_20260801_031043.log`，training accounting 为 `results/20260801_care_target_domain_race_gap_closure/m2_i_mmseg_care/training_accounting.csv`，receipts 为 `fold2_training_receipt.json` 和 `fold3_training_receipt.json`。这只是 terminal training completion，不是 final evaluation completion。

## M3_CARE_TDS

- 外部源码：无。使用本仓库 `CARETargetDomainSpecialist`，冻结 Dataset501 stock nnU-Net 并只读 `F0` 与 detached soft wall/LV context。
- 关键本地资产同 M0R。
- 已验证：在 `61220581 / htzhulab / g1807htzh01` 上 CUDA smoke PASS；fold2/fold3 四个独立 head 均有 finite gradient；final prediction 未使用 stock class4/5 logits。

## Shared Batch Manifests

M0R 和 M3 共享完全相同的 deterministic manifest：

- `results/20260801_care_target_domain_race_gap_closure/batch_manifest_fold2.jsonl`
  - sha256 `917a8312fd3bffdd45c1d6295ca16b04e02804639c4aec243804b799728d6d60`
- `results/20260801_care_target_domain_race_gap_closure/batch_manifest_fold3.jsonl`
  - sha256 `2a5599328357ca35978a6577b11f38fb97df8039da94067cfd5f7cf3ffce955c`
