自然判断：Batch7 新增的是候选生成和候选仲裁能力，不是数据边界或 backbone 变更。

Architecture deltas:
- Spatial dictionary receives prototype conditioning maps from rebuilt Batch7 memory.
- Proposal path split into anchor-independent discovery and anchor-confirmation branches.
- Refiner path is differentiable full-volume soft ROI instead of formal crop/bbox loop.
- Final pathology source uses learned proposal/refiner arbiter before existing bounded production gate.

Non-deltas:
- Fold, cases, train/validation split, label thresholds, backbone, encoder profile, and base retrieval policy were not changed.
- Cine, validation upload, fold expansion, and Batch8 were not touched.
