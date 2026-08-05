# CARE MyoPS Attempt3 Single-Slice Hotfix

This Docker context derives only from the frozen organizer-tested image:

```text
FROM care-myocardium-myops:attempt3-failed-base
```

It applies one runtime preprocessing safeguard to nnU-Net 2.7.0:
`compute_new_shape` keeps the original rounding expression and clamps the
resulting spatial dimensions to at least one voxel with
`np.maximum(new_shape, 1)`.

It does not copy models, checkpoints, `predict.py`, `entrypoint.sh`, or
requirements from the mutable repository context. It does not install packages,
download files, change the entrypoint, change TTA, change folds, change the
label map, or alter CineMyoPS.
