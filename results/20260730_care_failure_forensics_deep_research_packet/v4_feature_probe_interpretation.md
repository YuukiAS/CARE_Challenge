# V4 feature probe interpretation

The V4 probe uses all 80 T2-present cases with fixed 5-fold patient-level refolding. Outer cases are included only as read-only diagnostic evidence; no checkpoint, threshold, or postprocessing choice is selected from these folds.

## Scar top signals

- NNUNET_DECODER_L1 / P3_nnunet_scar_FP_vs_true_negative / logistic_regression: mean AUROC 1.000, mean AUPRC 1.000.
- NNUNET_ENCODER_L1 / P3_nnunet_scar_FP_vs_true_negative / logistic_regression: mean AUROC 1.000, mean AUPRC 1.000.
- NNUNET_ENCODER_L1 / P7_small_scar_vs_normal_myocardium / logistic_regression: mean AUROC 1.000, mean AUPRC 1.000.
- NNUNET_ENCODER_L2 / P3_nnunet_scar_FP_vs_true_negative / logistic_regression: mean AUROC 1.000, mean AUPRC 1.000.
- NNUNET_ENCODER_L2 / P7_small_scar_vs_normal_myocardium / logistic_regression: mean AUROC 1.000, mean AUPRC 1.000.

## Pure edema top signals

- NNUNET_DECODER_L4 / P6_nnunet_pure_edema_FP / logistic_regression: mean AUROC 0.998, mean AUPRC 0.998.
- NNUNET_DECODER_L2 / P6_nnunet_pure_edema_FP / logistic_regression: mean AUROC 0.996, mean AUPRC 0.996.
- PRISM_EDEMA_ROUTED_L1 / P6_nnunet_pure_edema_FP / logistic_regression: mean AUROC 0.996, mean AUPRC 0.996.
- PRISM_PRIVATE_LGE_L1 / P6_nnunet_pure_edema_FP / logistic_regression: mean AUROC 0.996, mean AUPRC 0.997.
- PRISM_PRIVATE_LGE_L2 / P6_nnunet_pure_edema_FP / logistic_regression: mean AUROC 0.996, mean AUPRC 0.997.

## Leakage controls

- Patient-level overlap: False.
- Single-class fold rows: 0.
- Controls run: CASE_VOLUME_ONLY_CONTROL, CENTER_ONLY_CONTROL, MODALITY_ONLY_CONTROL, PATIENT_ID_LEAKAGE_CONTROL, RANDOM_LABEL_CONTROL, SHUFFLED_ACROSS_PATIENT_CONTROL, SHUFFLED_WITHIN_PATIENT_CONTROL, SPATIAL_COORDINATE_ONLY_CONTROL.
