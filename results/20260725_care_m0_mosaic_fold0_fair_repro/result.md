MoSAIC 权重已经登记，但 native MoSAIC 复现还没有闭环；当前只能确认协议、通道、label 和几何审计框架，不能训练、不能上传，也不能把 MoSAIC 当成已完成 baseline。

machine_status: NEEDS_MOSAIC_SOURCE
reason: dry run only; native MoSAIC source/predictions not yet available
case_count: 44

| model_id | pathology | evaluated | gt_positive | mean_dice | mean_exact_hd | status |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| nnunet_fold0 | pure_edema | 0 | 0 |  |  | MISSING_PREDICTIONS |
| nnunet_fold0 | scar | 0 | 0 |  |  | MISSING_PREDICTIONS |
| native_mosaic | pure_edema | 0 | 0 |  |  | MISSING_PREDICTIONS |
| native_mosaic | scar | 0 | 0 |  |  | MISSING_PREDICTIONS |
| nnunet_anatomy_prior_mosaic_experts | pure_edema | 0 | 0 |  |  | MISSING_PREDICTIONS |
| nnunet_anatomy_prior_mosaic_experts | scar | 0 | 0 |  |  | MISSING_PREDICTIONS |
| care_candidate | pure_edema | 0 | 0 |  |  | MISSING_PREDICTIONS |
| care_candidate | scar | 0 | 0 |  |  | MISSING_PREDICTIONS |
