# CARE hard-case supplement review

这份补充图册只用于组会展示四个困难病例，不改变 CARE 当前科学状态，不恢复任何候选资格，也不重新选择检查点。

## Scope checks

- Cases included: Case3008, Case3009, Case3027, Case2012.
- Cases excluded: Case2019, Case2034, Case2021.
- Training, Slurm, validation upload, Docker upload, CURRENT.md edits, and wiki edits were not performed.
- M0R composition reused frozen outer replay helpers and fixed checkpoints: scar step 3500, pure edema step 4000.

## Bound model panels

- Case3008: nnU-Net=绑定, MoSAIC clean=yes, MoSAIC full/final=no, PRISM=no.
- Case3009: nnU-Net=绑定, MoSAIC clean=yes, MoSAIC full/final=no, PRISM=no.
- Case3027: nnU-Net=绑定, MoSAIC clean=yes, MoSAIC full/final=no, PRISM=no.
- Case2012: nnU-Net=绑定, MoSAIC clean=yes, MoSAIC full/final=no, PRISM=no.

## Slice selection

- Case3008: slice 9, rule `primary_gt_scar_plus_pure_edema_max_with_m0r_error_visible`.
- Case3009: slice 3, rule `primary_gt_scar_plus_pure_edema_max_with_m0r_error_visible`.
- Case3027: slice 5, rule `primary_gt_scar_plus_pure_edema_max_with_m0r_error_visible`.
- Case2012: slice 0, rule `primary_gt_scar_plus_pure_edema_max_with_m0r_error_visible`.

## Metric consistency

- Case3008: CPU_VISUAL_REPLAY_DIFFERS_FROM_OFFICIAL_CSV_VALUES against official outer_replay/casewise_metrics.csv.
- Case3009: CPU_VISUAL_REPLAY_DIFFERS_FROM_OFFICIAL_CSV_VALUES against official outer_replay/casewise_metrics.csv.
- Case3027: CPU_VISUAL_REPLAY_DIFFERS_FROM_OFFICIAL_CSV_VALUES against official outer_replay/casewise_metrics.csv.
- Case2012: CPU_VISUAL_REPLAY_DIFFERS_FROM_OFFICIAL_CSV_VALUES against official outer_replay/casewise_metrics.csv.

## Layout check

- page 1 Case3008: PASS.
- page 2 Case3009: PASS.
- page 3 Case3027: PASS.
- page 4 Case2012: PASS.

PDF: `/users/a/e/aereinh/CARE/docs/presentation/2026_08_01_care_group_meeting/CARE_hard_case_supplement_a3_landscape.pdf`
