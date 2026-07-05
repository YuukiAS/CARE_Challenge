# Source Line Evidence

Key source evidence checked:

- nnU-Net anchors are located and loaded in `scripts/training/run_srr_propref_myops_fold0.py:118-176`.
- no-T2 anchor edema is zeroed for unavailable T2 in `scripts/training/run_srr_propref_myops_fold0.py:164` and `scripts/training/run_srr_propref_myops_fold0.py:311-316`.
- baseline preservation loss uses confident correct anchor voxels in `scripts/training/run_srr_propref_myops_fold0.py:428-471`.
- edema proposal/loss masks use `t2_present` in `scripts/training/run_srr_propref_myops_fold0.py:483-571`.
- runtime prototype banks are fit/loaded by `scripts/training/run_srr_propref_myops_fold0.py:1098-1177` and `scripts/training/run_srr_propref_myops_fold0.py:1433`.
- pathology-aware decode is in `scripts/training/run_srr_propref_myops_fold0.py:681-700`.
- full-case prediction consumes anchor/component tensors in `scripts/training/run_srr_propref_myops_fold0.py:708-750`.
- no-T2 prediction sanity records no-T2 edema voxels in `scripts/training/run_srr_propref_myops_fold0.py:894-918`.
- anatomy distance/soft gate context is computed and exposed in `src/care_myocardium/models/srr_propref.py:287-307` and `src/care_myocardium/models/srr_propref.py:955-965`.
- ROI refinement uses anatomy, anchor evidence, distance support, and uncertainty in `src/care_myocardium/models/srr_propref.py:360-409`.
- local crop refinement includes `P_union/P_LV/P_RV` and distance channels in `src/care_myocardium/models/srr_propref.py:493-538`.
- baseline-preserving gate computes `anchor_logits + gate * bounded_delta` in `src/care_myocardium/models/srr_propref.py:572-640`.
- forward path wires anatomy ROI, scar/edema proposals, local refinement, and baseline gate in `src/care_myocardium/models/srr_propref.py:854-995`.
- no-T2 edema logits are blocked in `src/care_myocardium/models/srr_propref.py:934-936`.
- t2-masked edema loss is implemented in `src/care_myocardium/losses/srr_losses.py:39-46`.
