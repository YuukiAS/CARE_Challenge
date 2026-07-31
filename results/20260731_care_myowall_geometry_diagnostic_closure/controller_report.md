# MyoWall geometry diagnostic closure

这次诊断没有支持继续把 hard wall 坐标作为唯一病理入口。G0 已严格复现旧指标，但 G1 用 GT 解剖通过同一个 wall transform 后仍只有 25/32 例通过，失败五例全部仍失败；Case3029 也不是单纯 supported-slice denominator 错误。G3 的全局阈值清理在 pilot_inner 上只修好少数病例，CenterH LGE-only 四例仍系统失败。本任务没有启动四臂训练，也没有改 production geometry、访问 outer 或上传验证包。

## Machine Decision

controller_verification_decision: VERIFIED_COMPLETE
scientific_decision: HARD_WALL_REPRESENTATION_INVALID
operational_completion_status: COMPLETE
experiment_adequacy_decision: DIAGNOSTIC_COMPLETE_NO_FORMAL_TRAINING
contract_compliance_status: PASS
required_outputs_complete: PASS
validators_passed: PASS
all_jobs_terminal: TRUE
aggregation_complete: TRUE
git_commit_decision: COMMITTED df7833ccb98a2ad99e7f1af88f4ce81b96e3e450
git_push_decision: PUSHED_MAIN_VERIFIED df7833ccb98a2ad99e7f1af88f4ce81b96e3e450
next_required_action: RETURN_TO_PLANNER

## Threshold Winner

{"case_count": "144", "case_geometry_valid_rate": "0.013888888888888888", "fifth_percentile_roundtrip_dice": "0.1134755493758199", "hd95_metrics_computed": "True", "l1_distance_from_original_threshold": "0.25", "lv_threshold": "0.15", "median_roundtrip_hd95_mm": "7.745697711887631", "secondary_metrics_computed": "True", "selection_population": "pilot_train", "wall_threshold": "0.15"}

## Failed Five

- Case3029: wall_transform_or_GT_shape_failure
- Case8003: wall_transform_or_GT_shape_failure
- Case8022: wall_transform_or_GT_shape_failure
- Case8027: wall_transform_or_GT_shape_failure
- Case8028: wall_transform_or_GT_shape_failure

## CenterH

- Case8003: wall_transform_or_GT_shape_failure
- Case8022: wall_transform_or_GT_shape_failure
- Case8027: wall_transform_or_GT_shape_failure
- Case8028: wall_transform_or_GT_shape_failure
