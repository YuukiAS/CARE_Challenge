# CARE-SCF Step3 SafeScar Gate Pause Packet

第三个 major step 已完成：220-case MoSAIC scar OOF 通过 no-leakage audit，scar component dataset 构建完成，低容量 SafeScar logistic gate 已用 case-grouped CV 训练并输出 component decisions。

- controller_verification_decision: OPERATIONALLY_PAUSED_BY_USER_AFTER_STEP3
- goal_complete: false
- major_step3_status: PASS
- MoSAIC OOF: 220/220 cases, status=PASS
- scar components: 220, status=PASS
- gate: regularized_logistic_regression, component_count=220, case_grouped=True, grid=54, status=PASS
- decisions: {'retain': 188, 'suppress': 32}
- OOF help/harm labels: {'help_retained_tp': 181, 'help_suppressed_fp': 17, 'harm_false_suppression': 15, 'harm_retained_fp': 7}
- step4: paused by user; edema training/arbitration not started in this pause packet
- step5: paused by user; validation package/final packet not completed in this pause packet
- validation upload: false
- docker upload: false
- new Slurm allocation: false

Evidence root: `results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1`
Packet root: `results/care_scf/step3_safescar_gate_pause`
