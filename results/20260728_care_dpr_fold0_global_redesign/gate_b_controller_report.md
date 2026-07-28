# CARE-DPR Fold0 Gate B Report

结论：CARE-DPR fold0 formal 4000-step 训练和 Gate B outer evaluation 已完成；工程合同路径通过，但科学门未通过，因为 selected threshold 下所有候选均被拒绝，最终输出精确回落到 nnU-Net anchor，没有任何病理 Dice 改善超过 0.005。下一步只能人工决策是否返修 utility/threshold/curriculum，不能自动扩 folds、all-data fit、validation upload 或 Docker/runtime push。

State: AWAITING_HUMAN_ACCEPTANCE_DPR_GATE_B
Approval token: APPROVE_DPR_GATE_B
Formal expansion authorized: false

训练与恢复：
- seed=20260728；formal_training_credit=4000；actual_optimizer_steps=4000。
- Stage A1/A2/B steps=500/2000/1500；checkpoint reload=PASS；参数值与固定输出 exact=True/True。
- selected checkpoint=checkpoint_step04000.pt；selected utility threshold=0.5；outer fold0 未用于 checkpoint/threshold selection。

评估结果：
- complete16 scar Dice anchor/DPR=0.6933/0.6933；edema-zone=0.7522/0.7522；pure-edema=0.3944/0.3944。
- outer44 scar Dice anchor/DPR=0.5602/0.5602；edema-zone=0.5816/0.5816；pure-edema=0.7798/0.7798。
- scientific_gate=FAIL；failures=['no_pathology_improves_by_more_than_0.005']；help/harm complete16=0/0。

机制证据：
- two-pass full-volume inference PASS：overlap=0.5，Gaussian blending，pass1 聚合 shared feature/p_coarse/q_fn/q_fp，pass2 per-candidate refiner+utility；禁止 patch final label averaging。
- real candidates outer44=5652；scar ADD/REVISE=4708/90；edema ADD/REVISE=830/24。
- accept targets positive/negative=1012/4640；utility AUROC/AUPRC=0.5162/0.2148；oracle/realized gain=16.7763/0.0538。
- selected runtime accepted/rejected=0/5652；fixed threshold 0.3 would accept 5 and reject 5647 on outer44 mechanism audit, but train-side selected threshold remained 0.5.
- proposal recall scar/edema=0.7748/0.9688；proposal precision scar/edema=0.7008/0.5953。
- predicted ROI coverage scar/edema=0.6560/0.2907；predicted refiner Dice scar/edema=0.1930/0.3043。
- no-T2 exact-zero PASS；zero accepted candidates exact anchor PASS；all GPU processes terminal。

验证：
- DPR unit tests: 18 passed。
- A-R2 strict validator PASS；A-R2 consistency validator PASS；Gate B validator PASS。

主要证据路径：
- results/20260728_care_dpr_fold0_global_redesign/gate_b_summary.json
- results/20260728_care_dpr_fold0_global_redesign/gate_b_validator_report.json
- results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_model_summary.csv
- results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_mechanism_report.json
- results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_scientific_gate.json

source/config/test/evidence hashes 已记录在 checkpoint_notifications/dpr_gate_b.json。


## Evidence Hashes

- `results/20260728_care_dpr_fold0_global_redesign/gate_b_summary.json`: `53c5cb539f8a842b4120552ea18329647f7e8e11539813eca8d5cbf7ce211f75`
- `results/20260728_care_dpr_fold0_global_redesign/gate_b_validator_report.json`: `536eb23b036c8a3e191ff926ac789e932f735bb3a2fdf979535e21c5e51ec835`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_model_summary.csv`: `9a72b3c6baafcb1dd3241f9e5f8aae5b438cf5af03ccd2be59f487e7333bd9a5`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_casewise_metrics.csv`: `b882de9f7069cd4cf28c669fd1bd76f878ee8155077cec4c8a2007c79639fb4d`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_mechanism_report.json`: `4874ae40e601acb97c16169351e328e1dc368d15a53a6323c6a13ae3334580e5`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_scientific_gate.json`: `0caa82bbd32ad2fd4a761e7fa12337024a4b087545fc8944e66b99ff48345723`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_checkpoint_threshold_selection.json`: `c5665c7af92701cf8d903c8848e91f1b267d9c7e14136687127a793d8378ebc2`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_no_t2_safety_audit.csv`: `8f3a82146413d43657c5fb368cde2338eb4dfe30d199b8412599af1f0f33c1d7`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_help_harm.csv`: `d92b44084bae3c6f402d563c42ae2f8fae7db69dd1086d02996c284fc507547c`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_outer_candidate_rows.csv`: `97763ff9830ca22505544029ad8dd2aa46fa1ae9ffcdcdceffb32781ac0f5c93`
- `results/20260728_care_dpr_fold0_global_redesign/runtime/formal_fold0/gate_b_evaluation/gate_b_inner_candidate_rows.csv`: `080957946b3c117075de467a98f492865bbdcdf3b627c7051b59857a3be72ab2`
