# Production Call Graph

状态：未构建生产调用图。

原因：nnU-Net edema provenance gate 已写入本地审计，但当前主机没有 `docker` 命令，无法构建、加载或运行任务要求的两个 Docker image。为避免产生未经运行验证的生产入口，本控制器没有创建伪就绪的 Docker 调用图。

MyoPS 目标策略仍冻结为：MoSAIC scar source + nnU-Net pure-edema source + nnU-Net anatomy source，优先级为 scar > pure edema > anatomy。MoSAIC edema 权重不得进入 MyoPS 生产调用路径；由于 Docker 源未落地，本 packet 只能记录该禁止项，不能把它验证为运行时调用图事实。
