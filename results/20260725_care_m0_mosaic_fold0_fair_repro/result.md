MoSAIC 源码、权重路径和启动前检查已经就绪，但 native MoSAIC 的 fold0 预测还没有生成；当前可以开始正式 GPU inference，不能训练、不能上传，也不能把 MoSAIC 当成已完成 baseline。

machine_status: NEEDS_PREDICTIONS
reason: native MoSAIC source, entrypoint, and weights are ready; predictions have not been generated
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
