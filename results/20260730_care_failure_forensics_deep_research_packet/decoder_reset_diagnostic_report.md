# D0 pretrained identity replay diagnostic

结论：D0 已在冻结的 fold0 inner_select 12 例上完成。stock nnU-Net fold0 checkpoint 的
myops_edema Dice 为 0.923083，myops_scar Dice 为 0.922388，
foreground mean Dice 为 0.914594。这说明同一批病例、同一评价器下，
预训练 nnU-Net 本身可以给出高质量结果；PRISM 低分不能归因于 PDF、字体、评价器完全失效或内层病例不可分割。

运行边界：

- 使用既有 Slurm allocation `61220581`，`existing_allocation_overlap`；没有提交新的排队训练任务。
- 使用 checkpoint `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth`。
- 只在 `fold0_inner_select` 上推理和评估；未使用 `fold0_outer` 调参，未上传 hosted validation。
- nnU-Net 推理日志出现 multiprocessing 临时目录清理 `Device or resource busy` 警告，但命令 exit code 为 0，12 个目标 prediction 文件均存在。

证据文件：

- `decoder_reset_training_summary.csv`
- `decoder_reset_inner_casewise.csv`
- `decoder_reset_checkpoint_manifest.csv`
- `decoder_reset_comparison.csv`
- `results/20260730_care_failure_forensics_deep_research_packet/runtime/D0_FULL_PRETRAINED_IDENTITY/evaluation/evaluation_summary.json`
- `logs/ForensicsD0_61220581_20260730_000747.log`

下一步：D1-D3 decoder reset 诊断可以启动；feature probe、MoSAIC recipe decomposition、Cine temporal probe 仍需绑定输入/checkpoint 后才能执行。
