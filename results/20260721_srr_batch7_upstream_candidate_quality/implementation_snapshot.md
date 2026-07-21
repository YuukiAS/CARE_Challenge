自然判断：Batch7 的候选质量链路已接入并能在真实 Case2002/Case1002 batch 上产生非零干预和梯度；fixed 100-step 已过，但 formal300 没有达到继续 1200 的效果门槛。

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
- Real implementation interventions and checkpoint roundtrip: latest `59784603`, PASS.
- Fixed Case2002+Case1002 100-step overfit: `59783024`, PASS.

Formal300 stop gate:
- Formal300 job: `59789651`, COMPLETED `0:0`, elapsed `00:11:25`, node `g1807htzh01`.
- Actual optimizer steps: `300`.
- Full-volume eval steps: `100`, `200`, `300`.
- Continuation gate: FAIL.
- Mean positive pathology Dice delta: `0.0003021837774180077`, required `>=0.005`.
- Scar gt-positive Dice delta: `-0.0048258512122039895`.
- Edema gt-positive Dice delta: `0.005430218767040005`.
- Help/harm count: `23/35`.
- No-T2 edema exact zero and formal gradient gate passed.

Formal training status:
- formal300 completed and aggregated.
- formal1200 skipped by contract after failed step300 gate.
