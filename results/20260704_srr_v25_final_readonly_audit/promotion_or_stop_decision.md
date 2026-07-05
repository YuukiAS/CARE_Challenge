# Promotion Or Stop Decision

decision: `PROMOTE_DIAGNOSTIC_ONLY`

## Not Promoted As Challenge Candidate

Do not promote this route for validation packaging or upload. Same-split full
fold0 metrics do not beat nnU-Net in a meaningful way, and the checkpoints are
bounded 6-step mechanism probes.

## Not Scientific Stop

Do not mark `STOP_SRR_DIRECTION_NOT_SUPPORTED`. The packet is much closer to
the SRR-v2.5 contract than the earlier partial implementation, but the training
and Cine evidence are still not adequate for a broad scientific stop.

## Supported Stop Boundary

It is reasonable to stop the current bounded checkpoint packet as a
challenge-facing candidate. It is diagnostic-only evidence that:

- nnU-Net anchor preservation is necessary;
- the current retrieval/refinement/anatomy additions do not yet improve nnU-Net;
- Cine remains blocked at the full registration matrix level.
