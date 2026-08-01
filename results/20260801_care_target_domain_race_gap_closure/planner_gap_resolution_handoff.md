# Planner Gap Resolution Handoff

当前不是“四个模型都不行”。训练层面已经跑完的是 M0R/M1/M3 的 fold2/fold3；没有跑的是 M2，因为官方 I-MMSeg 权重/ViT 资产没有落地，合同禁止用 rank-channel 或空模型替代。现在真正卡住的是合同后半段：checkpoint 深审计、M0R step checkpoint fidelity、full-volume inner/outer evaluation、统一 aggregation 和 final validator。

## Current Published State

- repo: `YuukiAS/CARE_Challenge`
- branch: `main`
- latest pushed commit at this handoff: `f857c941fd748e7e008b739fc3c42f1ba8fe7fd8`
- result root: `results/20260801_care_target_domain_race_gap_closure`
- interactive allocation still verified through `htzhulab`: `61220581 / g1807htzh01 / NVIDIA H100 NVL`
- latest training/accounting commit: `3c1c348`
- latest checkpoint asset audit commit: `f857c94`

## What Actually Ran

| lane | fold2 | fold3 | current interpretation |
| --- | --- | --- | --- |
| M0R faithful nnU-Net control | Slurm job `61565286` completed `0:0` | pending job `61565287` cancelled, then interactive PID `4039804` completed | training complete, but step-checkpoint and LR/manifest fidelity gaps remain |
| M1 MyoPS-Net-L CARE | lane job `61576324` completed | lane job `61576324` completed | training complete, needs full-volume reconstruction/evaluation |
| M2 I-MMSeg CARE | not run | not run | official source pinned, external weights missing |
| M3 CARE-TDS | interactive `61220581` completed 4000 steps | interactive `61220581` completed 4000 steps | training complete, but model/loss fidelity and full-volume evaluation gaps remain |

## External Assets

### M1 MyoPS-Net

- source: `https://github.com/QJYBall/MyoPS-Net.git`
- required commit: `479f07028c5bdb12b405dc92212aa48ae6ba947a`
- current local checkout: `third_party/MyoPS-Net_PINNED`
- clone commands:

```bash
git clone https://github.com/QJYBall/MyoPS-Net.git third_party/MyoPS-Net_PINNED
git -C third_party/MyoPS-Net_PINNED checkout 479f07028c5bdb12b405dc92212aa48ae6ba947a
```

No extra M1 pretrained weights were used in the current CARE adapter. The current adapter uses pinned upstream `UNet`, `UNetEncoder`, and `UNetDecoderPlus`, with C0/LGE/T2 only and no T1/T2star placeholders.

### M2 I-MMSeg

- source: `https://github.com/zzzzzzl24/I_MMSeg.git`
- required commit: `90f46c4eb72924509895fcda6bc6a3b8c3316e66`
- current local checkout: `third_party/I_MMSeg_PINNED`
- Google Drive folder: `https://drive.google.com/drive/folders/1WHcpG8YlDlEdnlclbXKDZJANLX10iSq3?usp=drive_link`
- expected upstream assets:
  - `I_MMSeg_env.tar.gz`
  - `R50-ViT-B_16.npz`
  - `epoch_299.pth`
  - MyoPS380 raw/processed dataset only if institutional approval is granted
- expected CARE placement:
  - `third_party/I_MMSeg_PINNED/model/vit_checkpoint/imagenet21k/R50-ViT-B_16.npz`
  - `third_party/I_MMSeg_PINNED/weights/TU_Myops128/TU_pretrain_R50-ViT-B_16_skip3_epo300_bs24_lr0.001_128/epoch_299.pth`

Download command if the current account can access the Google Drive folder:

```bash
mkdir -p /users/a/e/aereinh/.tmp/codex-CARE/20260801_care_target_domain_race_gap_closure/i_mmseg_assets_raw
python -m gdown --folder 'https://drive.google.com/drive/folders/1WHcpG8YlDlEdnlclbXKDZJANLX10iSq3?usp=drive_link' -O /users/a/e/aereinh/.tmp/codex-CARE/20260801_care_target_domain_race_gap_closure/i_mmseg_assets_raw
```

If `gdown` is unavailable, install it in `env_CARE` or download manually from the browser into the same raw folder, then copy the two required model files to the expected CARE placement. Do not use MyoPS380 as CARE training data unless the planner explicitly authorizes a data-compliance path.

BiomedCLIP note: upstream I-MMSeg calls `open_clip.create_model_from_pretrained('hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224')`; first run needs HuggingFace access/cache unless the model is already cached.

## Remaining Gaps And Implementation Plan

### Gap 1: M0R is trained but not contract-faithful enough

Evidence:
- `checkpoint_reload_audit.json` shows M0R fold2/fold3 each have only `checkpoint_best.pth` and `checkpoint_final.pth`.
- Missing expected step checkpoints: `500,1000,1500,2000,2500,3000,3500,4000`.
- `nnUNetTrainerGapClosureM0R4000` currently records `LambdaLR_constant`, not the requested 250-step warmup plus per-step cosine decay to `1e-6`.
- The shared manifest currently records `step/case_id/input_order/shared_by_lanes`; it does not record crop coordinates, sampling stratum, augmentation values, and seed, and the nnU-Net dataloader does not consume it as a deterministic batch schedule.

Repair plan:
- Update `src/care_myocardium/nnunet/gap_closure_trainer.py` to use per-step AdamW schedule: 250-step warmup, then cosine decay to `1e-6`.
- Add an nnU-Net checkpoint hook that emits explicit copied/aliased files named `checkpoint_step00500.pth` through `checkpoint_step04000.pth`.
- Either implement manifest-bound batch sampling for M0R or record a planner-approved contract exception. If implementing, bind nnU-Net case order/crop RNG to the existing fold manifest and expand the manifest with crop coordinate, sampling stratum, augmentation parameters, and seed.
- Rerun M0R fold2/fold3 after the scheduler/checkpoint/manifest repair, because current artifacts cannot satisfy all-checkpoint inner selection.

### Gap 2: M1 has formal training but no full-volume evaluator

Evidence:
- M1 fold2/fold3 receipts show 60 epochs, 100 steps/epoch, `formal_training_credit: true`, no T1/T2star placeholders.
- M1 checkpoint grid exists through step6000.
- No full-volume reconstruction, per-case Dice/HD95/exactHD, lesion recall, remote FP, or help/harm table has been generated.

Repair plan:
- Fix `scripts/training/target_domain_gap_closure/run_m1_myopsnet_l_care.py` so future `training_accounting.csv` always uses stable fields: `fold,event,timestamp,epochs,steps_per_epoch,last_loss,device`.
- Add a deterministic M1 inference/evaluation script that loads each step checkpoint, slices Dataset501 inner cases, reconstructs full volumes, maps `seg_lge` scar and `seg_t2` pure-edema outputs back to label space, and writes per-checkpoint metrics.
- Use inner cases only for checkpoint selection; do not touch fold outer until global source selection is frozen.

### Gap 3: M2 is asset-gated, not scientifically failed

Evidence:
- source is pinned at `third_party/I_MMSeg_PINNED`.
- required Google Drive assets are not present.
- rank-channel substitute was explicitly not used.

Repair plan:
- Download and place `R50-ViT-B_16.npz` and `epoch_299.pth` as listed above.
- Verify text feature files already present under `third_party/I_MMSeg_PINNED/text_features/`.
- Add a CARE Dataset501 adapter that preserves I-MMSeg CLIP/text prior semantics without replacing them with handcrafted rank channels.
- Run preflight, then formal fold2/fold3 training/evaluation only after assets are present.

### Gap 4: M3 training ran, but architecture/loss fidelity is partial

Evidence:
- Current `CARETargetDomainSpecialist` freezes stock anatomy and trains scar, pure-edema, injury, and boundary heads.
- It uses one boundary head, not a two-channel boundary/distance head.
- Losses are simplified BCE losses; component-MIL, remote-FP, relation, and distance/boundary terms are incomplete.
- Final full-volume intervention/evaluation is not implemented.

Repair plan:
- Extend `src/care_myocardium/models/target_domain_gap_closure.py` with explicit boundary and distance outputs, not one overloaded boundary logit.
- Add targets for component-MIL, remote-FP suppression, pure-edema/injury relation, and boundary/distance regression using existing Dataset501 labels and stock anatomy context.
- Rerun M3 fold2/fold3 after fidelity repair if the planner requires strict M3 contract compliance.
- Implement full-volume M3 inference over every 500-step checkpoint and use inner-only selection.

### Gap 5: Unified selection and outer replay are not implemented

Implementation plan:
- Add one canonical evaluator under `scripts/evaluation/target_domain_gap_closure/`.
- Metrics required per lane/checkpoint/case: Dice, HD95, exactHD where available, precision, sensitivity, lesion recall, small-lesion behavior, remote FP, blood-pool-adjacent FP, component counts, volume ratio, and help/harm against same-fold stock nnU-Net.
- Inner selection must select global scar source and global edema source from fold2+fold3 inner cases only.
- Outer replay must be deterministic and one-shot after freeze: fold-specific stock anatomy plus global scar/edema source plus fixed scar priority.
- Include sentinel cases `Case3008`, `Case3009`, `Case2019`, `Case2034`, and `Case2021`.

### Gap 6: Final controller packet is not ready

Required finalization:
- Write final aggregation tables and failure atlas.
- Rerun mapper with actual M0R/M1/M2/M3 dataflow, not the old W0 mapper report.
- Run `scripts/validation/validate_target_domain_race_gap_closure.py --phase final`.
- Write `notification_brief.json` only after final validator/aggregation/commit/push state is terminal.
- Send notification only through `./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once`.

## Hard Boundaries

- Do not mark current state complete.
- Do not call current state blocked.
- Do not treat M2 as failed; it is asset-gated.
- Do not submit validation upload, Docker upload, or hosted metric claim.
- Do not create a new interactive allocation.
- For any existing interactive allocation query, use `squeue -u "$USER" -p htzhulab` and the exact `squeue -j <jobid>`/`scontrol show job <jobid>` checks recorded in `AGENTS.md`.
