自然判断：Batch7 的候选质量链路已接入并能在真实 Case2002/Case1002 batch 上产生非零干预和梯度，但 deployed final output 在固定 100 步内没有达到进入 formal300 的 gate。

Implemented:
- Rebuilt Batch7 prototype/memory asset from Batch6 selected checkpoint and fold0 training cases only.
- Full tensor sha256 hashing for prototype/memory tensors.
- Pre-M10 spatial memory query and `prototype_maps` injection into `M10TwoPassSpatialDictionary`.
- Dual-source discovery/confirmation proposal dictionaries with reliability softmax.
- `DifferentiableSoftROIRefinementHead` as Batch7 formal full-volume refiner.
- `PathologySourceArbiter` replacing fixed proposal/refiner half-average in formal path.
- Batch7 loss components for discovery, confirmation, source arbiter, and final pathology.
- Batch7 Slurm entrypoints for htzhulab and a100 mirror; no volta entrypoints.

Passed gates:
- Asset rebuild: `59767801`, PASS.
- Real implementation interventions and checkpoint roundtrip: `59768200`, PASS.

Failed gate:
- Fixed Case2002+Case1002 100-step overfit: latest `59775353`, FAIL.
- Actual final pathology relative decrease: `0.11222805524509555`.
- Required final pathology relative decrease: `0.20`.
- Other fixed checks passed: finite losses, discovery loss decrease, scar refiner decrease, source arbiter decrease, all required gradient groups nonzero, zero-anchor discovery nonzero, no-T2 edema exact zero, checkpoint reload delta zero.

Formal training status:
- formal300 not submitted.
- formal1200 not submitted.
