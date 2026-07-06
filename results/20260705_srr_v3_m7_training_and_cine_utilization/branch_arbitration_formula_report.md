# Branch Arbitration Formula Report

status: `REPAIRED_PENDING_TRAINING_MONITOR`

Code path: `src/care_myocardium/models/srr_propref.py` `BranchArbitrationGate.forward` now computes `branch_delta = clipped(srr_weight * bounded_delta + proposal_weight * proposal_delta + refiner_weight * refiner_delta)` and `final_logits = anchor_logits + branch_delta`. `proposal_weight` and `refiner_weight` therefore have a prediction effect in unit tests.
