# Result

Metric truth reconciliation completed with PASS semantics. The task graph was executed; strict validator passed and the known-bad suite passed 15/15 before commit. Machine truth is in `metric_truth_table.csv`; terminal status is in `metric_truth_receipt.json`.

Key conclusion: D0 0.922x is inner-select prediction-vs-GT Dice from stock nnU-Net, not prediction parity and not clean OOF/hosted validation. Clean fair local comparison remains nnU-Net vs MoSAIC clean OOF only. Hosted rows are reference rows with partial lineage unless exact package/upload bytes are bound.
