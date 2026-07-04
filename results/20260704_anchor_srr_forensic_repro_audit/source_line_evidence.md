# Source Line Evidence

## Model Forward And Anchor/Component Use

- `src/care_myocardium/models/srr_propref.py:502-508`: `SRRProposeRefineMyoPS.forward` accepts `x`, `availability`, `anchor_features`, and `component_features`.
- `src/care_myocardium/models/srr_propref.py:512-520`: `_evidence_features` receives anchors; scar dictionary receives anchors and components.
- `src/care_myocardium/models/srr_propref.py:523-552`: edema dictionary and both refinement heads receive anchor/component evidence.
- `src/care_myocardium/models/srr_propref.py:555-557`: no-T2 samples force edema logits to `-20.0`.
- `src/care_myocardium/models/srr_propref.py:574-600`: outputs expose anchor/component evidence, crop masks, prototype source, dictionary slot counts/metadata, valid masks, and diagnostics.

## Proposal Dictionary

- `src/care_myocardium/models/srr_propref.py:37-50`: prototype buffers initialize from deterministic axis prototypes, plus negative memory buffers.
- `src/care_myocardium/models/srr_propref.py:52-57`: a `load_prototype_bank` method exists, but this audit did not find committed runtime evidence that formal fold0 loaded train/OOF prototype banks before training.
- `src/care_myocardium/models/srr_propref.py:132-155`: proposal logits mix learned conv score, positive-vs-negative similarity, nnU-Net anchor logits, component logits, and anatomy prior.
- `src/care_myocardium/models/srr_propref.py:158-160`: edema proposals are blocked when T2 is unavailable.

## Crop Soft ROI Refinement

- `src/care_myocardium/models/srr_propref.py:210-215`: refinement is documented as bounded crop, not full-volume residual.
- `src/care_myocardium/models/srr_propref.py:357-381`: bounded crop consumes original lesion-relevant modality crop plus features, evidence logits, proposal logits, anatomy prior, anchor/component evidence, prototype similarities, uncertainty, distance support, and ROI.
- `src/care_myocardium/models/srr_propref.py:454-475`: scar refinement uses modality index 0 (LGE); edema refinement uses modality index 1 (T2).

## Multi-Slot Retrieval

- `src/care_myocardium/models/srr_v2_unet.py:59-64`: `ScaleRetrieval` states old one-shared-block plus one-private-block implementation is no longer used.
- `src/care_myocardium/models/srr_v2_unet.py:79-87`: `ScaleRetrieval` constructs `MultiSlotSRRRetrievalBlock` with shared, private, and interaction slots.
- `src/care_myocardium/models/srr_v2_unet.py:105-111`: retrieval forward passes `anchor_features` into the block.
- `src/care_myocardium/models/srr_v2_unet.py:166-207`: `SRRV2MyoPSUNet.forward` also accepts anchor/component features and forwards them into retrieval/proposal head.

## Runner Anchor Paths

- `scripts/training/run_srr_propref_myops_fold0.py:111-124`: finds nnU-Net fold validation `.npz` probabilities and `.nii.gz` hard predictions.
- `scripts/training/run_srr_propref_myops_fold0.py:127-148`: loads probabilities and connected component features for compact scar class 5 and edema class 4.
- `scripts/training/run_srr_propref_myops_fold0.py:151-170`: reads anchored case and zeroes edema anchor/component evidence when T2 is absent.
- `scripts/training/run_srr_propref_myops_fold0.py:229-241`: converts anchor/component tensors into dictionaries expected by the model.
- `scripts/training/run_srr_propref_myops_fold0.py:303-311`: full-case prediction tensors preserve no-T2 zeroing.
- `scripts/training/run_srr_propref_myops_fold0.py:518-519`: prediction/export calls `model(x, av, anchor_features=..., component_features=...)`.
- `scripts/training/run_srr_propref_myops_fold0.py:752-756`: validation loss path calls model with anchor/component dictionaries.
- `scripts/training/run_srr_propref_myops_fold0.py:891-907`: one-batch overfit path calls model with anchor/component dictionaries.
- `scripts/training/run_srr_propref_myops_fold0.py:1079-1084`: formal training path calls model with anchor/component dictionaries.

## Loss And Safety

- `src/care_myocardium/losses/srr_losses.py:36-49`: dense edema supervision is masked to T2-present samples.
- `src/care_myocardium/losses/srr_losses.py:108-117`: soft anatomy prior penalizes pathology outside union prior.
- `src/care_myocardium/losses/srr_losses.py:120-145`: total SRR loss combines anatomy, scar, T2-masked edema, prior, and retrieval regularization.

