A0 到 A3 的全体积补评已经完成，结论并不支持继续这条 A0-A3 机制路线：A3 在完整体积上没有保住上一轮 patch 里的改善，反而同时伤害 scar 和 T2-present pure edema。最直接的意义是，当前训练出来的 head/proposal 虽然能在局部 patch 改变标签，但放回完整心脏体积后会产生系统性退化；因此不应启动 ROI/refiner、不应扩 fold、不应上传 validation/Docker，也不应把它包装成可靠机制信号。

controller_verification_decision: VERIFIED_COMPLETE
scientific_decision: SYSTEMATIC_HARM
metric_contract_status: PASS
canonical_t2_present_count: 80
inner_select_count: 35
t2_present_inner_select_count: 7
fold1_outer_accessed: false
fold0_outer_images_accessed: false
new_training_started: false
validation_upload_authorized: false
docker_upload_authorized: false
roi_refinement_authorized: false

Scar full-volume summary:
- A0 Dice mean: 0.608383
- A1 Dice mean: 0.410022
- A2 Dice mean: 0.418862
- A3 Dice mean: 0.415120
- A3 vs A0 Dice delta: -0.193264
- A3 vs A0 help/harm/neutral: 4 / 29 / 2
- A3 scar lesion recall mean: 0.677656; A0: 0.649310
- A3 scar remote FP volume mean: 2870.602 mm3; A0: 247.270 mm3

Pure-edema full-volume summary:
- A0 Dice mean on 7 T2-present cases: 0.422034
- A1 Dice mean: 0.354815
- A2 Dice mean: 0.330769
- A3 Dice mean: 0.356724
- A3 vs A0 Dice delta: -0.065310
- A3 vs A0 help/harm/neutral: 0 / 5 / 2
- A3 pure-edema HD95 mean: 107.469567 mm; A0: 49.213573 mm

Most improved A3 vs A0 scar cases:
Case1017 (+0.155), Case1081 (+0.083), Case3008 (+0.076), Case6009 (+0.025)

Worst harmed A3 vs A0 scar cases:
Case8014 (-0.584), Case8012 (-0.488), Case8016 (-0.459), Case1046 (-0.349), Case2015 (-0.346), Case8030 (-0.338), Case1031 (-0.337), Case2021 (-0.305), Case5006 (-0.293), Case2010 (-0.281)

Worst harmed A3 vs A0 pure-edema cases:
Case2021 (-0.129), Case2024 (-0.124), Case2015 (-0.095), Case2010 (-0.063), Case2027 (-0.046)

Intervention reading:
A3 scar head/proposal both change final labels, but disabling them generally lowers scar Dice or does not repair the systematic A3-vs-A0 harm. A3 edema head/proposal also change final labels on T2-present full volumes, but edema Dice remains below A0 and HD95 worsens. This means the modules reach final labels, yet their learned direction is not reliable enough for full-volume use.

Slurm/runtime accounting:
- job_id: 61220581
- step_id: 60
- partition: htzhulab
- state: COMPLETED_STEP
- node: g1807htzh01
- log_path: /tmp/care_fvc_logs/full_volume_closure_61220581_60_20260731_043900.log
- runtime_output_path: /users/a/e/aereinh/.tmp/codex-CARE/20260731_care_myopath_a0_a3_full_volume_closure
- started_at_utc: 2026-07-31T08:39:12.360421+00:00
- completed_at_utc: 2026-07-31T08:43:51.288687+00:00

Checkpoint SHA status:
- A0: 8bceb20cae8920e87d43b14665a0db9dfd4f1204533d25a3cd6e40ad9de74111 (PASS)
- A1: 455d640da0114cd179f60daa562100e8e173733bbfc2ff89c42997b0a2623f22 (PASS)
- A2: 3108c4f9a6310ab41c8b0c09798e440ac0dc0a8f283529013c70de00273223e4 (PASS)
- A3: 36d02389f596ddf81ddce72399ed12ef81c5b1140a60732a29eeba9eda2e4c76 (PASS)

Required evidence files are listed in MANIFEST.md. Runtime NIfTI predictions remain outside git under the runtime output path above.
