# SRR-v2 Architecture Contract

Implemented first-pass contract for `srr_v2_multiscale_private_basic`:

- Input order: LGE, T2, C0.
- Availability order: LGE, T2, C0.
- Three modality-private encoder streams are preserved through three scales.
- Missing modality features are multiplied by the availability mask inside each modality encoder.
- Each scale has shared and modality-private retrieval experts; interaction experts are enabled unless `--disable-srr-v2-interactions` is set.
- Retrieval gates are task-specific for anatomy, scar, and edema.
- Anatomy, scar, and edema use separate U-Net-like decoders.
- Proposal variants expose evidence/proposal/final logits separately through the proposal-head output contract.
- Dense edema supervision remains T2-masked through `t2_masked_edema_loss`.

Formal first task launched:

- `srr_v2_multiscale_private_basic`, job `57094446_0`.

Deferred until capacity frees or basic route status is known:

- `srr_v2_multiscale_private_proposal`
- `srr_v2_proposal_uncertainty_hardneg`
- optional `srr_v2_light_refine`
