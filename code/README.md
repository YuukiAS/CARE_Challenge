# `code/` — Model Implementation Scripts

This tree holds model-specific preparation, conversion, training, inference, and export helpers. These scripts are implementation code called by [`jobs/`](../jobs/README.md) Slurm/local entrypoints.

## Layout

| Subfolder | Contents |
|-----------|----------|
| `nnUNet/` | Dataset conversion, full-train wrapper, smoke tests |
| `MyoPS-Net/` | Layout prep, training shell, export predictions |
| `U-MyoPS/` | Stage1/2 prep and run scripts, val export — see [`U-MyoPS/README.md`](U-MyoPS/README.md) |
| `CineMyoPS/` | Task025/Task026 prep, train/test shell, val export |

For direct cluster submission and benchmark orchestration, use `jobs/`.
