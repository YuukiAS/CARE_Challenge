
W3D matched training 没有运行短 smoke，也没有用 component F1 或 full-data 污染指标替代。现有 allocation 和磁盘可用，但任务要求的“同一保存初始 FinePathNet state”没有在本地证据树中找到；现有 `.pt/.pth` 是已训练 checkpoint，不能保证 T0/T1 只差 sampler 权重。因此 W3D 记录为 `NOT_RUN_RESOURCE_OR_ASSET_GUARD`，W4-W7 继续完成。
