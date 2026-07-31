# CARE-QIF v2 Controller Report

这次审计只回答两个前置问题：跨中心强度信号是否真实可迁移，以及 component-query 是否在完整 held-out center 上比同输入 dense control 更能找回 scar 小病灶且不过度增加远端假阳性。本报告不授权启动完整 CARE-QIF v2 训练，也不构成官方验证成绩。

- controller_verification_decision: VERIFIED_COMPLETE
- joint_scientific_decision: NO_GO_QIF_V2
- scar_intensity_decision: FAIL
- injury_intensity_decision: FAIL
- component_query_decision: COMPONENT_QUERY_FACT_FAIL
- intensity_rows: 26
- query_summary_rows: 4
- slurm_terminal: True
- strict_validator_status: PASS

未授权动作：未访问 outer/official validation，未上传 Docker，未推送额外远端分支，未启动完整 CARE-QIF v2。
