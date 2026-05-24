# Lane B Round03 Active Hosted Calibration Execution

Date: 2026-05-20

Plan metadata:
- Type: active round execution
- Lane: B, CineMyoPS / `myocardium_cinemyops`
- Round scope: Round03 hosted calibration preparation
- Status: completed
- Parent roadmap: `TODO.md`
- Parent registry: `docs/plans/care_myocardium_plan_registry_rules.md`
- Controller: `docs/plans/laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`
- Function: prepare validation-style QA and staging tree for the promoted `topology_lcc` Cine candidate while preserving the existing nnU-Net MyoPS branch
- Do not: train, submit Slurm, run inference, download weights, upload validation, alter historical packages, or change the MyoPS branch source

## 执行状态

本轮已完成。未训练、未提交 Slurm、未下载权重、未上传 validation、未创建 zip，且未修改 already submitted historical packages。

执行脚本：

```bash
./envs/env_CARE/bin/python -m py_compile scripts/diagnostics/laneB_round03_hosted_calibration_prep.py
./envs/env_CARE/bin/python scripts/diagnostics/laneB_round03_hosted_calibration_prep.py --run-id nnUNet_MyoPS+Cine_topology_lcc_20260520_round03
```

新增脚本：

- `scripts/diagnostics/laneB_round03_hosted_calibration_prep.py`

## 已读取/核对的控制文件

- `docs/plans/care_myocardium_plan_registry_rules.md`
- `docs/plans/laneB_round02_completed_cinemyops_topology_lcc_addendum.md`
- `docs/plans/laneA_round02_completed_myops_edema_targeted_smoke_addendum.md`
- `docs/plans/laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`
- `docs/plans/laneC_round03to05_governance_portfolio_repo_screening_da_plan.md`
- `docs/notes/baseline/care_myocardium_diagnostics_execution_results.md`
- `docs/notes/baseline/CineMyoPS_improvement_round10_topology_round2.md`
- `results/experiments/CineMyoPS_iteration_log.md`
- `README.md`

用户列出的旧路径中，以下文件在当前 registry 命名下不存在，因此按 `find docs results scripts -maxdepth 5 -type f | sort` 定位并使用对应新文件：

- `docs/plans/laneB_round2_topology_execution.md` -> `docs/plans/laneB_round02_completed_cinemyops_topology_lcc_addendum.md`
- `docs/plans/laneA_round2_targeted_execution.md` -> `docs/plans/laneA_round02_completed_myops_edema_targeted_smoke_addendum.md`
- `docs/plans/laneC_portfolio_repo_screening_da_plan.md` -> `docs/plans/laneC_round03to05_governance_portfolio_repo_screening_da_plan.md`
- `docs/plans/round2_execution_priority.md` -> current registry/controller files

## 输入来源

MyoPS branch 保持现有 nnU-Net conservative baseline，没有生成新的 MyoPS prediction：

- source tree: `results/submissions/care_myocardium_validation/upload_ready/20260518_030921__nnUNet_MyoPS+CineMyoPS_pathology_direct/submission_tree/MyoPS`
- manifest anchor: `results/submissions/care_myocardium_validation/upload_ready/20260518_030921__nnUNet_MyoPS+CineMyoPS_pathology_direct/manifest.json`
- source manifest MyoPS: `source=nnUNetv2_predict`, `folds=["0"]`, `checkpoint=checkpoint_best.pth`

Cine candidate 使用 promoted `topology_lcc` compact predictions：

- compact pred dir: `results/predictions/CineMyoPS_R8_validation_hd_repair/pathology_largest_component/fold_0`
- compact label semantics confirmed: `0=background`, `1=myocardium`, `2=LV`, `3=scar`
- raw mapping confirmed: `0->0`, `1->200`, `2->500`, `3->2221`

Previous official comparison anchor:

- pathology_direct package tree: `results/submissions/care_myocardium_validation/upload_ready/20260518_030921__nnUNet_MyoPS+CineMyoPS_pathology_direct/submission_tree`
- previous hosted-submitted package id: `nnUNet_MyoPS+CineMyoPS_pathology_direct_20260518_030921`

Expected validation cases:

- CineMyoPS validation: `data/CARE_Challenge/CineMyoPS_val`, 15 cases `Case1001`-`Case1015`
- MyoPS validation: `data/CARE_Challenge/MyoPS_val`, 15 cases `Case1001`-`Case1015`

## 输出路径

All Round03 outputs are under:

```text
results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration/
```

Generated files:

- `packaging_qc_summary.md`
- `raw_label_qc.csv`
- `case_level_topology_lcc_qc.csv`
- `diff_from_pathology_direct.csv`
- `candidate_package_manifest.txt`
- `hosted_calibration_candidate_readme.md`

Candidate staging tree:

```text
results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration/staging/nnUNet_MyoPS+Cine_topology_lcc_20260520_round03/submission_tree
```

Round03 initial pass did not create a zip. After user confirmation on 2026-05-20, a strict comparison zip was created from the QA-passed staging tree. It keeps the exact MyoPS branch from the user-specified previous 5-fold baseline package and changes only `CineMyoPS/`.

```text
results/submissions/care_myocardium_validation/upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/CARE-Myocardium-OrganAgent.zip
```

Manifest:

```text
results/submissions/care_myocardium_validation/upload_ready/20260520_113408__nnUNet5fold_MyoPS+Cine_topology_lcc_round03_RECOMMENDED/manifest.json
```

Zip check passed: 30 prediction files, roots `MyoPS/` and `CineMyoPS/`, 15 cases per branch. MyoPS hash match against the previous 5-fold baseline package passed for 15/15 files. No upload was performed.

Upload-ready directories were later cleaned in place to timestamp-first names. The temporary alternate Round03 package was removed to avoid duplicate package folders.

## QA 结果

| gate | result |
| --- | --- |
| Cine raw label subset is legal `{0,200,500,2221}` | pass |
| Cine compact labels remain legal `{0,1,2,3}` | pass |
| raw mapping keeps `3 -> 2221` | pass |
| Cine case list matches validation cases | pass, 15/15 |
| MyoPS case list matches validation cases | pass, 15/15 |
| raw `2221` non-empty for each Cine case | pass, 15/15 |
| fallback required/used | none |
| raw `2221` component count | pass, 1 component in all 15 cases |
| MyoPS branch copied unchanged by file hash | pass |
| staging tree file count | pass, 30 files |
| zip/upload created | no |

Aggregate Cine raw `2221` QC:

| metric | value |
| --- | ---: |
| cases | 15 |
| total topology_lcc raw `2221` voxels | 49263 |
| previous pathology_direct raw `2221` voxels | 58952 |
| removed raw `2221` voxels vs pathology_direct | 9689 |
| mean raw `2221` components | 1.0000 |
| mean largest component fraction | 1.0000 |
| raw `2221` bbox gap to anatomy | 0.0 mm for all cases |

Per-case QC table is in:

- `results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration/raw_label_qc.csv`
- `results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration/case_level_topology_lcc_qc.csv`

Pathology-direct diff table is in:

- `results/diagnostics/care_myocardium/laneB_cine/round03_hosted_calibration/diff_from_pathology_direct.csv`

## Candidate 与 official pathology_direct 的差异

The staged candidate keeps the same MyoPS branch source and changes only the Cine branch from official `pathology_direct` raw outputs to compact `topology_lcc` converted with the unchanged CARE Cine mapping.

Observed Cine differences:

- raw `2221` total decreases from `58952` to `49263` voxels.
- removed raw `2221` voxels vs pathology_direct: `9689`.
- raw `2221` components decrease to `1` for every validation case.
- largest component fraction becomes `1.0` for every validation case.
- raw label subset stays legal and label histograms are recorded per case.
- bbox gap to anatomy remains `0.0 mm` for every case; center-distance/bbox/volume are recorded per case for hosted HD-risk inspection.

## 结论

QA 通过。新一轮可手动提交的 zip 已准备好，但它仍然只是 hosted-metric calibration experiment，不是最终模型。

建议提交时的解释目标：

- 验证 hosted `myocardium_cinemyops` 是否对 raw `2221` topology/HD 敏感。
- 验证 local class_3 HD95/component 改善是否能映射到 hosted HD 改善。
- 若 hosted HD 明显改善，可保留 LCC 作为 short-term calibration repair；若 hosted 指标仍差，应停止继续调 topology guard，转向 motion/strain/pretrained cine route。
