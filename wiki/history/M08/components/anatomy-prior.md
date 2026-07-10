# 解剖先验

## 历史分析原文迁移

### 1.4 Anatomy prior：有实现，但仍然依赖内部 anatomy head 和 anchor context，没有被证明是强解剖定位器

`AnatomyDistanceROIPrior` 确实实现了 `p_union`、`p_lv`、`p_rv`、union/LV/RV distance、uncertainty、scar/edema soft gate，并且 no-T2 时把 edema gate 置零。 forward 里 proposal/refiner 都消费这些 anatomy context：scar/edema dictionary 接收 task-specific anatomy soft gate logits，refiner 接收 P_union/P_LV/P_RV、distance map、uncertainty 和 task gate channel。summary 里也把 anatomy distance ROI prior 标记为 runtime consumed。

但它的强度仍然有限。它不是 CineMA/CorSeg 这种外部强 anatomy teacher，也不是一个充分训练的独立 anatomy-first cascade。它是同一个小模型内部 anatomy head 预测出的 soft prior，再叠加 nnU-Net anchor uncertainty/context。这个设计比纯后处理强，但没有证明“anatomy prior 本身”解决了 lesion localization。M8 子组结果显示 edema-positive/T2-present 仍然下降，说明 anatomy prior 没有把 edema 支撑区域学好。
