# M10 Architecture Delta Draft

Task key: `20260711_srr_v3_m10_complete_mechanism_repair`

Phase: `draft_after_wave1_merge`

## Draft Delta

Wave 1 adds the shared M10 implementation surface for the SRR-v3 complete mechanism repair:

- exact 16-slot shared/private/interaction dictionary metadata and residual expert implementation;
- M10 spatial dictionary module with voxelwise routing and two-pass lesion-conditioned retrieval surface;
- D0-D3 M10 PropRef variant declarations;
- independent Pattern-SIP loss separate from semantic retrieval regularization;
- separate memory alignment loss path rather than aliasing prototype diversity;
- cross-fitted prototype memory with no-T2 edema rejection;
- M10 final probability relation with exact no-T2 edema zero in wave1 smoke evidence;
- wave-specific config and fidelity tests.

## Files With Draft Architecture Impact

```text
src/care_myocardium/models/srr_blocks.py
src/care_myocardium/models/srr_spatial_dictionary.py
src/care_myocardium/models/srr_dictionary_memory.py
src/care_myocardium/models/srr_propref.py
src/care_myocardium/losses/srr_losses.py
configs/srr_v3_m10_complete_repair.yaml
```

## Wiki Status

Root wiki files are not updated in this draft pass. M10 remains `candidate_unreviewed`, and `wiki/current_state.yaml` must remain on M09 until independent M10 runtime review and a later reconciliation task.

## Open Runtime Evidence

The following remain missing until later waves:

- formal D0-D3 MyoPS runtime training and aggregation;
- hard-negative refresh and no-nnU-Net-context retrain;
- pair-valid MyoPS alignment train/control;
- component causal interventions;
- CineMA adapter, learned registration, registration gate, and learned temporal dictionary.
