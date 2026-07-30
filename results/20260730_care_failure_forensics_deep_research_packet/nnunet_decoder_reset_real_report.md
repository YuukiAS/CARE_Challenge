# Real nnU-Net Decoder-Reset Forensics

结论：真实 nnU-Net 路线已经把 PRISM 旧 wrapper 排除在外。D0-D3 均使用
`nnUNetTrainer_500epochs` 派生的真实 trainer、`nnUNetPlans`、`3d_fullres`
PlainConvUNet、官方 patch sampling/augmentation、deep-supervision 六类 loss，以及
fold0 `actual_train -> inner_select` 的冻结诊断 split。全部 GPU step 顺序运行在
Slurm allocation `61220581`、节点 `g1807htzh01.ll.unc.edu`、GPU `NVIDIA H100 NVL`。

## Results

| variant | train protocol | pure edema label4 Dice | scar label5 Dice | foreground mean Dice |
|---|---:|---:|---:|---:|
| D0_FULL_PRETRAINED_IDENTITY | no training; full stock checkpoint | 0.923082832 | 0.922379592 | 0.949999949 |
| D1_DECODER_RESET_ENCODER_FROZEN | 6 x 250 steps; encoder frozen | 0.000000000 | 0.546972404 | 0.509675952 |
| D2_DECODER_RESET_TOP_ENCODER_TRAINABLE | 12 x 250 steps; stages 4-6 + decoder trainable | 0.266405051 | 0.710793253 | 0.635188627 |
| D3_FULL_MODEL_SHORT_FINETUNE | 4 x 250 steps; full checkpoint, LR 1e-5 | 0.922549772 | 0.922683020 | 0.949944190 |

## Interpretation

D0 proves that the stock fold0 nnU-Net checkpoint, evaluator path, geometry, and
inner_select case set can reproduce a strong segmentation baseline. The weak D1
result shows that encoder-only inheritance plus a randomly initialized decoder
does not recover the strong baseline under a short diagnostic training budget.
D2 improves when upper encoder stages are allowed to adapt, but remains far below
D0, especially for pure edema. D3 preserves the D0 baseline after short full-model
fine-tuning, which argues that the actual_train pipeline itself is not destructive
when the decoder and full network state are retained.

The immediate forensic implication is that PRISM-style low performance is
consistent with decoder reset / incomplete decoder inheritance and insufficient
recovery, not with nnU-Net being intrinsically unreproducible on the inner_select
cases.

## Evidence

- `nnunet_decoder_reset_real_summary.csv`
- `nnunet_decoder_reset_real_casewise.csv`
- `nnunet_decoder_reset_prediction_manifest.csv`
- `nnunet_decoder_reset_real_aggregation_receipt.json`
- `runtime/nnunet_decoder_reset_real/g1_d0_identity_20260730T0658Z/`
- `runtime/nnunet_decoder_reset_real/g3_d1_encoder_frozen_20260730T0659Z/`
- `runtime/nnunet_decoder_reset_real/g3_d2_top_encoder_trainable_20260730T0706Z/`
- `runtime/nnunet_decoder_reset_real/g3_d3_full_finetune_20260730T0721Z/`
