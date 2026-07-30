# MoSAIC V2 recipe decomposition


G4 已完成为两层证据：M0/M1 使用既有 clean OOF held-out 预测与 GT；M2-M10 使用 `/users/a/e/aereinh/MoSAIC/code/source` 源码和 `/users/a/e/aereinh/MoSAIC/code/weights` 权重在 GPU 上拆解 full-data final recipe。

关键边界：full-data recipe 运行在训练命名空间病例上，因此只证明模型配方、阈值、TTA 和后处理如何改变输出，不作为公平 validation 分数。

- casewise: `results/20260730_care_failure_forensics_deep_research_packet/mosaic_recipe_decomposition_casewise.csv`
- summary: `results/20260730_care_failure_forensics_deep_research_packet/mosaic_recipe_decomposition_summary.csv`
- receipt: `results/20260730_care_failure_forensics_deep_research_packet/mosaic_recipe_decomposition_receipt.json`
