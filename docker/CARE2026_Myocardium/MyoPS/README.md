# CARE2026 MyoPS Frozen Production Source

This source context implements the frozen final MyoPS graph for the workstation
Docker build. It combines MoSAIC repo-final scar with Dataset501 5-fold nnU-Net
anatomy and pure edema:

- MoSAIC scar: `models/mosaic/myops/coarse.pt` and `models/mosaic/myops/fine_scar.pt`.
- nnU-Net: `models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/.../fold_0..fold_4/checkpoint_best.pth`.
- Output priority: scar > pure edema > anatomy > background.

The MyoPS context intentionally excludes and refuses MoSAIC `coarse_edema.pt`
and `edema.pt`.
