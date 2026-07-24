# W1 Implementation Snapshot

Decision: PASS_READY_FOR_CONTROLLER_VERIFICATION

Scope executed: same-scope W1 repair for CARE SRR cascade rescue. No W2 preflight/overfit, Slurm, packaging, or push was performed.

## Current Repair

- Fixed `confident_anchor_preserve` so its mask is exactly `anchor_prediction_equals_GT_and_anchor_max_probability_ge_0.80`.
- The preserve loss now applies `SmoothL1(z_final_pathology,z_anchor_pathology)` on confidently correct voxels regardless of whether the ground-truth voxel is pathology or non-pathology/background.
- Added focused synthetic evidence that a confidently correct background voxel contributes nonzero gradient to the scar pathology-channel preserve term.

## W1 Evidence

- `./envs/env_CARE/bin/python -m pytest tests/care_mm/test_care_srr_cascade_rescue.py -q` -> `8 passed`.
- The model exposes explicit W1 forward inputs and synthetic tests perturb each input to verify head wiring.
- Anatomy channels 0-3 remain exact anchor; no-T2 edema correction remains exact identity.
- Loss helper supervises final composed logits or `edema_zone_aux_logit` only; raw deltas are not referenced.
- Prototype helper has synthetic evidence for own-shard exclusion, case-level cap semantics, no no-T2 edema contribution, and fail-closed insufficient-bank behavior.
- Source checkpoints were CPU metadata-loaded with `torch.load(map_location="cpu", weights_only=True)` in W1 repair; no source forward or training was run.

## W2-Pending Only

- Real runtime source-cache parity.
- Full anchor tensor/grid roundtrip.
- 200-step overfit and full gradient matrix receipt.
- Checkpoint roundtrip.
- Real known-bad fixture suite.

## Hashes

- git HEAD: `6b9834c6f20416392a540535056c7196a4c429f3`
- origin/main: `6b9834c6f20416392a540535056c7196a4c429f3`
- resolved contract sha256: `4ba2714e75202a1129f617f169245551f4d85bd6a21fddea9579184ae3e9a848`
- model sha256: `934b77a61b5d29f805084697934a7be60a32f95ab38c33dfcfc118f644ee3e92`
- loss helper sha256: `ed3c9bfb9719693cc21c079e243d79425cecc018dafd7b8d4cd26498b605d945`
- prototype helper sha256: `2ea341e31e9a50de5a306de106df7392b436ae72151ffc7ce1c6f8814bae89bd`
- test sha256: `b93357cfe46a248735a2f9e9f330444f5f3f0c365a6b35945048ca84feaffaa6`
