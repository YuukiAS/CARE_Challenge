
220-case clean OOF scar 的 MoSAIC 均值为 0.392438，nnU-Net 均值为 0.577502，差值为 -0.185063。这与 hosted scar 0.6965 排名相反，最合理解释是 hosted row 结合了 full-data/selection、validation 域偏移、15-case 抽样和未绑定 exact recipe，而不是 clean MoSAIC 架构本身已被证明优于 nnU-Net。

因此最终科学结论是：MoSAIC 家族归属已确认，但 exact hosted package/checkpoint/recipe 未绑定；MoSAIC、SafeScar、MMRD、Cascade 均不能作为最终 Docker 的主动分割组件。唯一可执行架构是 `NNUNET_ONLY_DOCKER`，病种独立 fallback 为保持 nnU-Net identity 输出。
