# Loss Stage Status

| formal_variant | script_alias | stop_reason | stage_step_counts | first_train_loss | last_train_loss | loss_decrease |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `anchored_srr_v25_full` | `srr_propref_shared_dual_dict` | `max_steps` | `{'evidence_warmup': 4801, 'low_lr_calibration': 2399, 'proposal_dictionary': 9600, 'soft_roi_refinement': 7200}` | 3.9987473487854004 | 1.372961401939392 | 2.6257859468460083 |
| `anchored_scar_precision_edema_safe` | `srr_propref_scar_precision` | `validation_plateau_patience` | `{'evidence_warmup': 4801, 'low_lr_calibration': 1199, 'proposal_dictionary': 9600, 'soft_roi_refinement': 7200}` | 4.074131965637207 | 0.5363304615020752 | 3.537801504135132 |
| `anchored_conservative_cascade_no_proto_or_frozen_proto` | `srr_propref_no_proto_cascade` | `validation_plateau_patience` | `{'evidence_warmup': 4801, 'low_lr_calibration': 1199, 'proposal_dictionary': 9600, 'soft_roi_refinement': 7200}` | 3.702603578567505 | 0.4265343248844147 | 3.27606925368309 |
