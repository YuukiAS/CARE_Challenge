# Mapper Report Final

A0/A1 use the full stock encoder-decoder-output path; no encoder-only inheritance or decoder reset was used. A2 adds independent scar and edema global heads. A3 adds scar/edema proposal heads and proposal logits enter final logits with the frozen 0.5 coefficient. Scar and edema heads do not share parameters, and no-T2 edema probability stayed at 0.0 in terminal training receipts.

Architecture scope stayed inside `src/care_myocardium/models/care_myopath_pilot.py` and task-specific training/job files. Production PRISM, stock nnU-Net source, MoSAIC source, wiki, fold locks, validation packaging, and production evaluator were not modified.

Mapper limitation: result CSVs are patch-proxy diagnostics, not full-volume evaluator truth; therefore gates that depend on HD95, exact HD, lesion recall, remote FP, and full A0 help/harm remain unverified.
