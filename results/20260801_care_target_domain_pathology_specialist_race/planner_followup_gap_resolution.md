这次需要更正给 GPT planner 的结论：四个 model 并没有都完整训练并失败。当前可信结论是：M0 已经完成 fold2/fold3 正式训练和外层评价，确实低于 stock nnU-Net；M1、M2、M3 只完成了 preflight 或资产检查，暴露的是实现/资产缺口，不是模型科学失败。原 `scientific_decision: NO_GO_TARGET_DOMAIN_RACE` 只能作为“本轮没有可上传候选”的操作结论，不能当作“四条模型路线都被实验证伪”的科学结论。

# Planner Follow-up Gap Resolution

- task_key: `20260801_care_target_domain_pathology_specialist_race`
- created_for: GPT planner follow-up
- created_at: `2026-08-01`
- supersedes_planning_interpretation_of: commit `9f302fe`
- original packet root: `results/20260801_care_target_domain_pathology_specialist_race/`
- authorized scope of this note: clarify gaps, asset sources, download/implementation plan, and next planner decision; no validation packaging/upload/hosted metric claim.

## Corrected Lane Status

| Lane | What actually ran | Current evidence | Real gap | Can Codex handle without new external asset? | Planner action |
| --- | --- | --- | --- | --- | --- |
| M0 TD-NNUNET | Formal fold2/fold3 target-domain fine-tuning, 4000 optimizer steps per fold, full outer eval. | `m0_td_nnunet/m0_vs_stock_outer_summary.csv`; mean edema delta `-0.034462`, scar delta `-0.043167`, foreground delta `-0.022349`. | No implementation gap. Scientific result is negative against same-case stock baseline. | Yes, but rerun is not useful without a new hypothesis. | Treat as completed negative control. Do not upload. |
| M1 MYOPSNET-L-CARE | Preflight only. Slurm job completed but gave no formal training credit. | `m1_myopsnet_l_care/preflight_report.json` status `PREFLIGHT_NEEDS_IMPLEMENTATION`; local `third_party/MyoPS-Net` exists. | CARE complete-trimodal full-volume adapter, split binding, training wrapper, full-volume reconstruction, and evaluator are missing. | Mostly yes. Official code is already locally present, but should be pinned/audited before formal run. | Authorize adapter/wrapper implementation, then fold2/fold3 formal training. |
| M2 I-MMSEG-CARE | Asset preflight only. | `m2_i_mmseg_care/preflight_report.json` status `LANE_BLOCKED_EXTERNAL_ASSET`; `third_party/I_MMSeg_PINNED` missing. | Official source/assets absent. Contract forbids replacing it with hand-crafted rank channels. | No. Needs official source and assets first. | Download/pin source and public assets, then implement CARE adapter. |
| M3 CARE-TDS | Stock parity audit only; no formal training. | `m3_care_tds/preflight_report.json` shows fold2/fold3 stock parity PASS. | Independent pathology heads, direct-gradient losses, and matched batch descriptor are missing. | Yes. No external asset needed. | Highest-priority immediate implementation lane. |

## External Assets and Download Plan

### M1 MYOPSNET-L-CARE

Official source:

- Repository: `https://github.com/QJYBall/MyoPS-Net`
- Paper/DOI from README: `10.1016/j.media.2022.102694`
- License shown by GitHub repository page: MIT
- Current remote pin checked during this audit: `479f07028c5bdb12b405dc92212aa48ae6ba947a`
- Local source already present: `third_party/MyoPS-Net`
- Local preflight observed git head: `87a24c9754232325905fe4abf45666d97b0b6213`

The README describes a dataset layout built around `train_set/train_image`, `train_set/train_gd`, `val_set/val_image`, `val_set/val_gd`, `test_set`, plus `train.txt`, `validation.txt`, and `test.csv` slice lists. It also exposes training via `main.py` and prediction via `predict.py`. That means CARE cannot just point the old repository at nnU-Net-style full-volume data and call it formal.

Recommended source pinning command if planner wants a clean pinned copy rather than reusing the existing local tree:

```bash
cd /users/a/e/aereinh/CARE
git clone https://github.com/QJYBall/MyoPS-Net.git third_party/MyoPS-Net_PINNED
cd third_party/MyoPS-Net_PINNED
git checkout 479f07028c5bdb12b405dc92212aa48ae6ba947a
git rev-parse HEAD
```

CARE implementation work needed before formal M1 credit:

1. Build a CARE exporter from `split_receipt.json` and nnU-Net preprocessed fold2/fold3 data into the MyoPS-Net slice-list format.
2. Restrict modalities to CARE-available complete tri-modal channels: C0/bSSFP, LGE, and T2. Do not silently invent T1/T2* inputs.
3. Bind labels explicitly to CARE pathology labels, especially class 4 edema and class 5 scar.
4. Add full-volume reconstruction from slice predictions back to the CARE case geometry.
5. Run one-case preflight: dataset export, forward pass, finite loss, save/reload, inference reconstruction, and evaluator invocation.
6. Only after that, run the same fold2/fold3 outer protocol used by M0.

### M2 I-MMSEG-CARE

Official source and publication:

- Repository: `https://github.com/zzzzzzl24/I_MMSeg`
- PubMed PMID: `41967142`
- DOI: `10.1016/j.media.2026.104072`
- Current remote pin checked during this audit: `90f46c4eb72924509895fcda6bc6a3b8c3316e66`
- Local required source path from existing preflight: `third_party/I_MMSeg_PINNED`
- Google Drive asset folder from official README: `https://drive.google.com/drive/folders/1WHcpG8YlDlEdnlclbXKDZJANLX10iSq3?usp=drive_link`

The PubMed abstract states that I-MMSeg uses modality-specific intensity priors as text prompts, a CLIP-based prior encoder, an intensity-prior-guided cross-modal feature enhancement module, and a class feature modulation module. It also states that the source code and MyoPS380 dataset are available through the GitHub repository. The GitHub README says the code and assets are intended for peer review/reproducibility verification and lists these packages:

- `I_MMSeg_env.tar.gz`
- `R50-ViT-B_16.npz`
- `epoch_299.pth`
- `MyoPS380 dataset (raw + processed; available upon approval)`

Official README placement requirements:

```text
third_party/I_MMSeg_PINNED/
  model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz
  weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth
  MyoPS380_dataset/
    Raw_data/
    Processed_data/
```

Recommended source pinning:

```bash
cd /users/a/e/aereinh/CARE
git clone https://github.com/zzzzzzl24/I_MMSeg.git third_party/I_MMSeg_PINNED
cd third_party/I_MMSeg_PINNED
git checkout 90f46c4eb72924509895fcda6bc6a3b8c3316e66
git rev-parse HEAD
```

Recommended asset acquisition:

```bash
cd /users/a/e/aereinh/CARE
mkdir -p third_party/I_MMSeg_assets
# If gdown can access the public folder:
gdown --folder 'https://drive.google.com/drive/folders/1WHcpG8YlDlEdnlclbXKDZJANLX10iSq3?usp=drive_link' -O third_party/I_MMSeg_assets
```

If `gdown` cannot list/download the folder because Google requires browser confirmation or account approval, the correct failure packet is not a model failure. Record the exact Google Drive error and ask the planner/user to download the four packages manually into `third_party/I_MMSeg_assets/` or another declared local asset directory. After download, record hashes:

```bash
cd /users/a/e/aereinh/CARE
find third_party/I_MMSeg_assets -maxdepth 3 -type f | sort
sha256sum third_party/I_MMSeg_assets/* 2>/dev/null || true
```

CARE implementation work needed before formal M2 credit:

1. Pin the official repo and copy/link assets into the README-required paths.
2. Decide whether to use the packed `I_MMSeg_env.tar.gz` or build a separate CARE-compatible environment. Do not contaminate the active CARE torch env if dependencies conflict.
3. Confirm whether `epoch_299.pth` is used only for initialization/inference or as a required reproduction checkpoint; record this in the lane packet.
4. Adapt I-MMSeg data loading to CARE C0/LGE/T2 target-domain fold2/fold3 data.
5. Preserve real text/intensity-prior machinery from the official implementation. Do not substitute hand-written rank-channel shortcuts.
6. Run one-case preflight with official source/assets before any Slurm training.

MyoPS380 boundary: the official README says the dataset is available upon approval. For CARE formal fold2/fold3 training, MyoPS380 is not automatically required unless the planner explicitly authorizes paper reproduction, pretraining reproduction, or cross-dataset transfer. If the Drive package blocks on approval, M2 should be reported as `ASSET_APPROVAL_REQUIRED`, while M3/M1 can continue.

### M3 CARE-TDS

No external asset is required. This is the fastest lane to salvage because the stock nnU-Net weights, plans, and parity checks already passed for fold2/fold3.

Required implementation:

1. Add a CARE-TDS wrapper around the stock `PlainConvUNet` that captures final decoder features before the stock segmentation layer.
2. Preserve anatomy/stock compatibility for non-pathology outputs, but prevent final pathology predictions from directly reading stock class 4/5 logits.
3. Add independent heads:
   - scar head for class 5;
   - pure-edema head for class 4 edema not already explained by scar/injury;
   - injury head for shared pathology support;
   - boundary or distance-transform head for lesion boundary supervision.
4. Initialize heads from stock decoder features where justified, but audit that final scar/edema gradients flow through the new heads/losses rather than through reused stock label4/label5 logits.
5. Implement `TDSPathologyLoss` or equivalent with scar Dice/CE, edema Dice/CE, injury support loss, lesion-presence/MIL term, boundary/distance term, and a soft consistency term preventing pure edema from exceeding injury support.
6. Add a matched batch descriptor hash. Since M0 was already run without a descriptor, the planner must choose either:
   - rerun M0 with descriptor for exact batch-order proof, or
   - accept same split/case-list proof and require M3 to emit the descriptor going forward.
7. Preflight gates before Slurm training:
   - model build/import;
   - one forward pass;
   - finite scalar loss;
   - backward pass with nonzero gradients in new heads;
   - save/reload;
   - one-case full-volume inference/eval;
   - known-bad rejection if final class4/5 predictions are wired directly to stock logits.
8. After preflight, run fold2/fold3 with the same outer split and 4000-step budget as M0, then aggregate against stock and M0.

## Planner Decision Recommendation

The next GPT planner instruction should not ask Codex to “explain why all four failed.” That premise is wrong. It should say:

```text
请把 commit 9f302fe 视为 M0 完整 no-go + M1/M2/M3 缺口审计，不要视为四模型终局失败。下一步授权 Codex 在 main 上继续同一 target-domain pathology race 的修复：优先实现 M3 CARE-TDS，因为无外部资产且 stock parity 已过；并行整理 M1 MyoPS-Net CARE wrapper；M2 只在官方 I_MMSeg source/assets 下载并 pin 成功后进入 formal preflight。任何 lane 在 formal fold2/fold3 training/eval 前都不得写 scientific no-go；只有 M0 已经有正式 negative result。不得 validation packaging/upload，不得 hosted metric claim，不得 route promotion。
```

Recommended execution order:

1. M3 first: implement no-asset CARE-TDS heads/losses/preflight, then submit fold2/fold3 if gates pass.
2. M1 second: pin/audit MyoPS-Net, implement CARE complete-trimodal exporter/wrapper/reconstruction, then formal run.
3. M2 third: download official I-MMSeg source/assets; if Drive or approval blocks, document asset blocker and continue M3/M1 instead of stopping all work.
4. Keep M0 as completed negative control; do not rerun unless planner requires batch-descriptor parity proof.

## Stop Conditions

- Stop as `NEEDS_PLANNER_DECISION` if planner must choose whether M0 batch-descriptor rerun is required.
- Stop as `ASSET_APPROVAL_REQUIRED` only for M2 if the Google Drive assets or MyoPS380 approval cannot be obtained.
- Stop as `NEEDS_IMPLEMENTATION_REPAIR` if M1 or M3 preflight fails due to code wiring, gradient audit, save/reload, or full-volume reconstruction.
- Do not stop at Slurm submitted/pending/running state as completion.
- Do not claim leaderboard improvement or package/upload validation results from this follow-up without explicit planner/user authorization.

