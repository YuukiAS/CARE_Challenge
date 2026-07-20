# Batch4 Architecture Delta Final

status: `ARCHITECTURE_DELTA_RECORDED_PRE_REVIEW`

Batch4 exercises the existing SRR M10 D3 hierarchical memory/proposal/refinement path with a full-4scale encoder and base channels 32. The controller packet adds terminal evidence for:

- exact optimizer budget enforcement at `1800` optimizer steps;
- post-budget waiting without extra `optimizer.step()` calls until the minimum 1800-second loop duration is satisfied;
- schema-v2 checkpoint reload into three runtime modes using the same selected checkpoint;
- separate raw OOF anchor manifest hash and compact training-summary anchor hash accounting.

No new Cine path, route branch, validation upload path, or hosted metric interface was added. The architecture delta is evidence accounting for Batch4 only and remains pre-review.
