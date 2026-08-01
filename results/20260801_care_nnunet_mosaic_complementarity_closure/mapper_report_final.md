# Mapper report

架构影响很小：新增的是只读证据拼表与 validator，不改变模型训练、推理组合、阈值或验证上传路径。

- New builder: `scripts/evaluation/complementarity/build_nnunet_mosaic_complementarity.py`
- New validator: `scripts/validation/validate_nnunet_mosaic_complementarity.py`
- New tests: `tests/complementarity/test_bucket_semantics.py`
- Output namespace: `results/20260801_care_nnunet_mosaic_complementarity_closure/`

No architecture diagram update is required beyond wiki/current-state note because this is evidence closure, not a model-path change.
