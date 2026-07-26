
最终 Docker 只应执行唯一架构：`NNUNET_ONLY_DOCKER`。

MyoPS scar、MyoPS edema 和 CineMyoPS 均以已验证的 nnU-Net export path 为主。任何 MoSAIC、SafeScar、MMRD 或 Cascade 分支都不能在 runtime 中改变最终 mask；若未来作为研究分支存在，必须默认 identity fallback 到 nnU-Net 输出，并在病种、模态、checkpoint、cache 或 validator 任一失败时保持 nnU-Net 原样。
