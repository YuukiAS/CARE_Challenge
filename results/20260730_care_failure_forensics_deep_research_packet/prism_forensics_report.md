# PRISM 13-checkpoint replay

结论：G2 已在 fold0 inner_select 上重放 W3 formal v2 的 13 个 checkpoint，固定 scar/edema threshold 为 0.5，并为每个 checkpoint/case 保存 scar 与 edema raw probability。该证据用于后续 PRISM curve、step3000 选择、pure edema/scar 分离和 component on/off 分析；尚未等同于 P1-P11 全部完成。

- checkpoint_count: 13
- case_count: 35
- metric rows: 1365
- raw probability rows: 455
- selected checkpoint by edema_zone mean Dice: step 2500
