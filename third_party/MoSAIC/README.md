# MoSAIC external baseline assets

MoSAIC is registered here as an external baseline candidate for CARE fold0 fair
reproduction. This directory keeps a lightweight repo-visible index plus a
vendored copy of the public MoSAIC source, not the checkpoint store.

- Compatibility asset root: `/users/a/e/aereinh/MoSAIC`
- Canonical workspace: `/users/a/e/aereinh/MoSAIC`
- Canonical weights: `/users/a/e/aereinh/MoSAIC/code/weights`
- Canonical source clone: `/users/a/e/aereinh/MoSAIC/code/source`
- Paper truth workspace: `/users/a/e/aereinh/MoSAIC/paper`
- Public source: `https://github.com/IndeedLiu/MoSAIC`
- Vendored source path: `third_party/MoSAIC/source`
- Vendored source commit: `d334bd1fb2a99dbbc230510590cd8e3ee08cc377`
- Native entrypoint: `third_party/MoSAIC/source/scripts/infer_and_submit.py`
- Manifest: `third_party/MoSAIC/weights_manifest.json`
- Runtime preparation: `scripts/inference/prepare_mosaic_inference_runtime.py`
- Fair protocol config: `configs/baselines/mosaic_fold0_fair.yaml`
- Inference wrapper: `scripts/inference/run_mosaic_fold0_fair_inference.py`
- Evaluation wrapper: `scripts/evaluation/evaluate_mosaic_fold0_fair_comparison.py`

Boundaries:

- evaluation-only
- no training
- no validation upload
- no production-path dependency
- no `.pt`, `.nii.gz`, prediction tree, or runtime cache in git

The canonical `/users/a/e/aereinh/MoSAIC` workspace now separates paper and code. Downloaded weights live under `/users/a/e/aereinh/MoSAIC/code/weights`; root `myops/` and `cinemyops/` are compatibility symlinks so the existing CARE `MOSAIC_ROOT=/users/a/e/aereinh/MoSAIC` path still works. CARE also keeps a vendored public-source copy under `third_party/MoSAIC/source` for repo-visible fair reproduction. Native MoSAIC inference
may be started only through the explicit evaluation/preflight path; a clone or
model-load smoke test is not a completed fair comparison metric.
