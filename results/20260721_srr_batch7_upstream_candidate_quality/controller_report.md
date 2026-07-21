自然判断：Batch7 上游候选链路已经通过固定两例可学习性证明；下一步可以按合同进入 formal300，但当前 packet 还不能验收为完整 Batch7。

controller_verification_decision: NEEDS_REPAIR

Evidence:
- Asset rebuild passed on job `59767801`.
- Real intervention and checkpoint roundtrip passed on latest job `59784603`.
- Fixed-overfit passed on job `59783024`.
- Fixed-overfit required final pathology relative decrease >= `0.20`.
- Latest actual final pathology relative decrease = `0.20564072041957518`.
- Discovery proposal decrease = `0.9393179540866319`.
- Scar refiner repair decrease = `0.7297403798614842`.
- Source arbiter decrease = `0.6591003537125409`.
- All required gradient groups were nonzero.
- Case1002 no-T2 edema ROI/residual/correction remained exactly zero.

Execution decision:
- formal300 is allowed next but was not submitted before this source-state commit.
- formal1200 is not allowed before the formal300 continuation gate.
- No a100 mirror was needed; htzhulab jobs started before the 900-second mirror threshold.
- No volta job was submitted.
- No push/upload/Cine/fold expansion/Batch8/reviewer action was performed.
