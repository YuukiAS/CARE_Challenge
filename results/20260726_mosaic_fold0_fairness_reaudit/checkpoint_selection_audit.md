MoSAIC fold0 的旧 inference 入口优先读取 `fine_scar/best.pt`，因此会加载 epoch 75 的 scar checkpoint；upstream submission 入口在存在时优先读取 `best_scar.pt`，本次 clean 修正按这个规则使用 fold0 epoch 190 checkpoint。

- best_scar 与 best_pathology SHA256 相同: False
- pathology checkpoint selected: `results/20260725_care_myops_mosaic_fold0_reproduction/runtime/fold0/fine_scar/best_scar.pt`
- full-data Google Drive 权重只用于污染诊断，不进入 fair clean comparison。
