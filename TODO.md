- U-MyoPS:

    - Stage1 和 Stage2 之间确实需要额外桥接脚本/数据导出步骤。现有仓库里 Stage1 的 gen_res/checkpoint 不会自动变成 Stage2 需要的 nnU-Net v1 Task。
    - 最终跟别的模型做可比 benchmark 时，应以 Stage2 pathology segmentation 的结果作为 U-MyoPS 的最终输出，不是 Stage1。Stage1 更像前置配准/心肌阶段。当前我没有改 U-MyoPS 训练 split，只在文档里明确了这一点，并保留了“统一评估只评 protocol val cases”的接口位。