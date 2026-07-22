# Implementation Snapshot

self_assessed_status: partial_static_wave0_wave1_evidence

The lightweight BR2 path is implemented behind `enable_batch7_decomposition_br2`.
SIP reads `all_center_beta` and `source_eligibility_mask`, not the current batch effective beta.
Formal 400-step Slurm runs are not represented by this static packet.
