用户确认的事实是：leaderboard scar Dice 0.6965 属于 MoSAIC submission。本任务不重新裁决模型家族。

现在可以绑定的事实是：MoSAIC final public repo 为 `IndeedLiu/MoSAIC`，commit `d334bd1fb2a99dbbc230510590cd8e3ee08cc377`；本地 `/users/a/e/aereinh/MoSAIC/code/source` 是同一 commit；final pretrained weights 已下载到 `/users/a/e/aereinh/MoSAIC/code/weights`，7 个 checkpoint SHA 见 `download_summary.json`；final inference recipe 由 `scripts/infer_and_submit.py`、`docker/myops/predict.py` 和 `docker/cinemyops/predict.py` 绑定。

仍未绑定的是：2026-07-06 09:13:49 或 2026-07-08 19:08:16 当时上传的原始 ZIP bytes、ZIP SHA256 和上传回执。根据 repo 注释与 leaderboard 行，7/8 更接近 final recipe：MyoPS scar 保持 0.6965，Cine 从 0.1878 提升到 0.2058/约 0.2069，符合 Cine previous-best V1/V2 ensemble 回滚；7/6 很可能 MyoPS 分支相同但 Cine 分支较弱。
