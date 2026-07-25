# MoSAIC external baseline assets

MoSAIC is registered here as an external baseline candidate for CARE fold0 fair
reproduction. This directory is intentionally a lightweight index, not the
checkpoint store.

- Default asset cache: `/users/a/e/aereinh/MoSAIC`
- Manifest: `third_party/MoSAIC/weights_manifest.json`
- Fair protocol config: `configs/baselines/mosaic_fold0_fair.yaml`
- Inference wrapper: `scripts/inference/run_mosaic_fold0_fair_inference.py`
- Evaluation wrapper: `scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py`

Boundaries:

- evaluation-only
- no training
- no validation upload
- no production-path dependency
- no `.pt`, `.nii.gz`, prediction tree, or runtime cache in git

The current `/users/a/e/aereinh/MoSAIC` cache contains downloaded weights and
download manifests, but no native MoSAIC source code. Until source code or a
validated native entrypoint is available, native MoSAIC reproduction must report
`NEEDS_MOSAIC_SOURCE` rather than fabricated metrics.
