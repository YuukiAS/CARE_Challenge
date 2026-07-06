# Architecture Gap Table

| gap | evidence | blocker |
| --- | --- | --- |
| Follow-up2 primary training has not completed yet. | `followup2_training_adequacy.csv` | Blocks ready; packet is monitor/evidence, not route promotion. |
| Cine temporal dictionary depends on usable non-reference registration. | `registration_same_subset_matrix.csv` | Blocks Cine readiness when no usable row exists. |
