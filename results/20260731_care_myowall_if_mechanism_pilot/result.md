# CARE-MyoWall-IF mechanism pilot terminal result

本轮机制试验没有进入正式训练。冻结 fold1 nnU-Net 的预测几何在 pilot_inner 上没有通过前置门，因此按合同停止，不能用 GT geometry、Cartesian fallback 或降低门限继续四臂比较。

## Decision

- controller_verification_decision: `VERIFIED_COMPLETE`
- scientific_decision: `STOP_GEOMETRY_NOT_RELIABLE`
- metric_dependency_status: `PASS`
- geometry_gate: `FAIL`
- C0/W1/W2/W3: `NOT_STARTED_GEOMETRY_GATE_FAILED`

## Geometry Gate

- case geometry valid rate: `0.84375` (required `>=0.95`)
- median wall roundtrip Dice: `0.9998856896450612` (required `>=0.96`)
- 5th-percentile wall roundtrip Dice: `0.7068920140479127` (required `>=0.90`)
- median roundtrip HD95 mm: `0.0` (required `<=2.0`)
- failed cases: `Case3029, Case8003, Case8022, Case8027, Case8028`

## Boundary

- fold1 outer was not read.
- validation/Docker upload was not started.
- full long training was not started.
- formal C0/W1/W2/W3 8000-step training was not started.

## Evidence

- `results/20260731_care_myowall_if_mechanism_pilot/metric_dependency_receipt.json`
- `results/20260731_care_myowall_if_mechanism_pilot/pilot_split_receipt.json`
- `results/20260731_care_myowall_if_mechanism_pilot/asset_freeze_receipt.json`
- `results/20260731_care_myowall_if_mechanism_pilot/stock_parity_report.json`
- `results/20260731_care_myowall_if_mechanism_pilot/geometry_gate_report.json`
- `results/20260731_care_myowall_if_mechanism_pilot/geometry_casewise_metrics.csv`
- `results/20260731_care_myowall_if_mechanism_pilot/slurm_terminal_snapshot.json`
- `prompts/routes/handoffs/CURRENT.md`
- `wiki/README.md`
