# Final Submission Model Ledger

本次只冻结和打包 Planner 指定模型，不进行模型选择、checkpoint 比较、TTA/no-TTA 比较或 hosted lineage 竞赛。

## MyoPS

- scar: MoSAIC repo-final scar, `coarse.pt` + `fine_scar.pt`.
- pure edema: Dataset501 5-fold nnU-Net `checkpoint_best.pth`, folds 0-4, default TTA, raw class 4.
- anatomy: same nnU-Net classes 1/2/3.
- priority: scar > pure edema > anatomy > background.
- MoSAIC `coarse_edema.pt` and `edema.pt` are excluded from the MyoPS bundle and are not loaded.

## CineMyoPS

- MoSAIC repo-final Cine: `coarse.pt`, `fine_v1.pt`, `fine_v2.pt`.
- z-spacing ensemble: 4/8/16 mm.
- TTA and final decode are fixed to the repo-final Cine recipe.

## Historical Hosted Lineage

`0.6691` remains `UNRESOLVED_NOT_CLAIMED`. This is recorded as historical attribution uncertainty only and is not used as a packaging blocker.

