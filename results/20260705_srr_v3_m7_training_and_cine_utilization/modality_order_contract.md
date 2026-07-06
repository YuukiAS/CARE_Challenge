# Modality Order Contract

Implementation channel order is `LGE,T2,C0`; therefore `availability[:,1]` is T2. The route diagram may use semantic order `LGE,C0,T2`, so all code-level no-T2 checks must follow implementation order, not diagram order. Evidence paths: `src/care_myocardium/models/srr_propref.py`, `src/care_myocardium/losses/srr_losses.py`, `scripts/training/run_srr_propref_myops_fold0.py`.
