Dear CARE2026 organizers,

Thank you for checking the submitted containers. We corrected the MyoPS archive for the single-slice preprocessing failure; CineMyoPS remains unchanged.

The corrected image is derived from the exact previously submitted MyoPS archive and retains the same five-fold nnU-Net checkpoints and inference configuration. The only change is a preprocessing safeguard that clamps resampled spatial dimensions to at least one voxel; outputs on all 15 normal public validation cases remain bitwise identical to the original image.

Corrected archive: `MyoPS-OrganAgent-corrected.tar.gz`
Image tag after load: `care-myocardium-myops:organagent`
SHA256: `fcf1c67a2123ab655a8e6c32dc46e6d98feaa43f41c698c6969aebfaa51f79ff`
Size: `4742235545`
Download link: https://drive.google.com/open?id=1ATXgeTn99xFZAB3SLH1-aSpTuIb5EO5a

The run contract is unchanged:

```bash
docker run --rm --network none -v /path/to/input:/input:ro -v /path/to/output:/output care-myocardium-myops:organagent
```

The container writes MyoPS predictions under `/output/myops`. The correction only addresses single-slice preprocessing. We do not claim any new validation metric, and no challenge or validation predictions are attached.

Please reevaluate MyoPS with this corrected archive when convenient.

email_sent=false
