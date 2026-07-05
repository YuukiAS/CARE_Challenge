# Runtime Evidence

## Full Fold0 Eval

`results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval/manifest.json`
reports:

- status: `COMPLETE`
- fold: `0`
- eval cases: `44`
- completed variants: `6`
- mode: `eval_only_existing_bounded_checkpoints_no_training_no_upload`

Each of the six expected variants has:

- 88 prediction NIfTI files;
- 176 case metric rows;
- 36 subgroup rows;
- a same-split nnU-Net help/harm packet.

The Slurm job `57896202` completed with `ExitCode 0:0`, elapsed `00:32:37`.

## Cine Runtime

`results/20260704_cine_full_cinema_registration/` includes:

- ANTsPy SyN smoke on `Case1001`, frame 9 -> frame 0;
- VoxelMorph PyTorch untrained adapter probe on the same pair;
- `voxelmorph_adapter_probe.csv` and `syn_voxelmorph_probe.csv`.

The VoxelMorph probe is near identity and not a successful learned-registration
result.
