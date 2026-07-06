# Code Diff Summary

First-party code paths modified for M6:

- `src/care_myocardium/models/srr_v2_unet.py`: audited encoder profiles and dictionary config wiring.
- `src/care_myocardium/models/srr_blocks.py`: named pair-specific dictionary configurations.
- `src/care_myocardium/models/srr_propref.py`: M6 variants, segmentation context interface, explicit branch arbitration.
- `src/care_myocardium/losses/srr_losses.py`: M6 expanded total loss.
- `scripts/training/run_srr_propref_myops_fold0.py`: M6 variant/profile/loss wiring.

```text
scripts/training/run_srr_propref_myops_fold0.py |  49 +++-
 src/care_myocardium/losses/srr_losses.py        | 129 ++++++++++
 src/care_myocardium/models/srr_blocks.py        |  55 +++-
 src/care_myocardium/models/srr_propref.py       | 329 ++++++++++++++++++++++--
 src/care_myocardium/models/srr_v2_unet.py       |  51 +++-
 5 files changed, 589 insertions(+), 24 deletions(-)
```
