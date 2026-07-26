# Control vs previous submission delta

本次 control 只改变组合方式：MyoPS 使用既有 nnU-Net 5-fold prediction tree，Cine 使用 20260518 pathology_direct tree。当前 interactive job 没有可见 CUDA，且用户要求不再提交 Slurm job，因此没有重新跑 GPU 推理。

- New ZIP: `results/submissions/care_myocardium_validation/upload_ready/20260726_nnunet5f_control__nnUNet5F-control/CARE-Myocardium-OrganAgent.zip`
- ZIP SHA256: `155b1997afc0ccdea77b210e880c7405db49be0bfc64f5331f86e97047238e62`
- MyoPS raw submission hash match vs 20260519 5-fold baseline: `15/15`
- Cine raw submission hash match vs 20260518 pathology_direct: `15/15`
- validation_upload_performed: `false`
- slurm_submission_performed: `false`
