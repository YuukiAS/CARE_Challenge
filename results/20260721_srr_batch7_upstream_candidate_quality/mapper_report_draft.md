自然判断：架构变更集中在 SRR MyoPS Batch7 的上游候选质量路径；主风险不是模块缺失，而是 bounded deployed final path 对 fixed-overfit 改善的传递不足。

- `ProposalDictionary`: adds discovery and confirmation proposal branches plus two-source reliability fusion.
- `SRRProposeRefineMyoPS.forward`: queries rebuilt prototype/memory before M10 spatial dictionary and passes prototype maps into M10.
- `DifferentiableSoftROIRefinementHead`: replaces discrete crop refiner for Batch7 formal variant with full-volume differentiable ROI/residual computation.
- `PathologySourceArbiter`: learns proposal/refiner source weights; no fixed `0.5 * proposal + 0.5 * refiner` formal path remains.
- `checkpoint.load_srr_checkpoint`: supports non-strict architecture-extension warm start while preserving strict default.
- Batch6 final/gate/no-T2 semantics remain: anchor-bounded correction, production gate, and no-T2 edema zeroing are still active.
