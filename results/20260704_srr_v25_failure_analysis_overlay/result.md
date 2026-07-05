# Result: 20260704 SRR-v2.5 Failure Analysis Overlay

status: `EXECUTED_UNAUDITED`
self_assessed_status: `HARD_SUBGROUP_AND_BOUNDED_MATRIX_OVERLAYS_VERIFIED_NEEDS_FULL_FOLD0_AND_AUDIT`
domain_evidence_label: `PREFLIGHT_SMOKE_ONLY`

## 执行摘要

本任务先把 failure analysis 从 one-case smoke 扩展到一个显式 hard-subgroup
packet。新增 runner 参数 `--eval-case-ids`，用 1-step tiny CPU runtime 直接
导出 `Case1002,Case2002,Case3004,Case3011`，覆盖 no-T2 safety、T2-present
GT-positive edema、CenterC scar 和 CenterC edema。随后用
`scripts/evaluation/srr_failure_analysis_overlay.py` 生成 7 张 scar/edema
overlays、taxonomy、proposal/refiner、dictionary、nnU-Net context 和
residual/gate traces，并用 same-split nnU-Net help/harm comparator 做对照。

当前 hard-subgroup evidence 说明 decode guard 在这些 case 上没有再出现
remote FP flooding：所有 SRR remote FP count 都是 `0`。主要剩余失败模式不是
remote island，而是 CenterC/T2-present edema 的低覆盖/边界问题。例如
`Case3011` edema Dice `0.266909`、HD95 `34.266133`，taxonomy 标为
`boundary_or_extent_error;crop_or_roi_undercoverage`。该任务仍不能通过完整
completion gate，因为 evidence 只有 1-step smoke，不是 formal bounded matrix，
且 spatial proposal/dictionary maps 仍未导出。

后续补充把 8-row bounded matrix 中的 6 个非 identity 机制 rows 也送入同一
overlay/taxonomy 管线：`srr_propref_shared_dual_dict`,
`srr_propref_no_proto_cascade`, `srr_propref_scar_precision`,
`srr_v25_no_local_refine`, `srr_v25_no_anatomy_roi`, `srr_v25_no_anchor`。
产物位于 `bounded_matrix_overlay/`，共 42 张 overlay、96 行 taxonomy。该补充
确认 anchor-enabled rows 主要仍是 neutral/boundary 类错误；`srr_v25_no_anchor`
集中出现 remote island / proposal flooding / refiner overcorrection，与 bounded
matrix help/harm 中 remote-FP 大幅增加一致。

## 读取文件

- `prompts/tasks/20260704_srr_v25_failure_analysis_overlay.md`
- `results/20260704_srr_v25_failure_analysis_overlay/hard_subgroup_runtime/variants/srr_propref_shared_dual_dict/*`
- `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation/Case1002.nii.gz`

## 修改文件

- `scripts/evaluation/srr_failure_analysis_overlay.py`
- `scripts/training/run_srr_propref_myops_fold0.py`
- `results/20260704_srr_v25_failure_analysis_overlay/case_error_taxonomy.csv`
- `results/20260704_srr_v25_failure_analysis_overlay/overlay_manifest.md`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case1002_myops_scar_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case2002_myops_scar_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case2002_myops_edema_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case3004_myops_scar_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case3004_myops_edema_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case3011_myops_scar_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/overlays/Case3011_myops_edema_failure_overlay.png`
- `results/20260704_srr_v25_failure_analysis_overlay/proposal_vs_refiner_breakdown.csv`
- `results/20260704_srr_v25_failure_analysis_overlay/dictionary_gate_trace.csv`
- `results/20260704_srr_v25_failure_analysis_overlay/nnunet_context_trace.csv`
- `results/20260704_srr_v25_failure_analysis_overlay/residual_gate_trace.csv`
- `results/20260704_srr_v25_failure_analysis_overlay/hard_case_summary.md`
- `results/20260704_srr_v25_failure_analysis_overlay/pre_training_decision.md`
- `results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay/`
- `results/20260704_srr_v25_failure_analysis_overlay/MANIFEST.md`

## 运行命令

```bash
./envs/env_CARE/bin/python scripts/training/run_srr_propref_myops_fold0.py \
  --variant srr_propref_shared_dual_dict \
  --fold 0 \
  --device cpu \
  --base-channels 4 \
  --encoder-profile tiny_3scale \
  --max-steps 1 \
  --max-runtime-seconds 900 \
  --val-every 1 \
  --overfit-steps 1 \
  --min-overfit-loss-decrease -999 \
  --limit-train-cases 8 \
  --limit-val-cases 1 \
  --prototype-bank-cases 8 \
  --eval-case-ids Case1002,Case2002,Case3004,Case3011 \
  --out-root results/20260704_srr_v25_failure_analysis_overlay/hard_subgroup_runtime
```

Result: exit `0`.

```bash
./envs/env_CARE/bin/python scripts/evaluation/srr_failure_analysis_overlay.py \
  --case-ids Case1002,Case2002,Case3004,Case3011 \
  --srr-run-dir results/20260704_srr_v25_training_ablation_matrix/bounded_matrix/variants/<variant> \
  --output-dir results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay/<variant> \
  --fold 0
```

Result: six non-identity bounded matrix variants exited `0`.

```bash
./envs/env_CARE/bin/python scripts/evaluation/aggregate_srr_v25_overlay_packets.py \
  --root results/20260704_srr_v25_failure_analysis_overlay/bounded_matrix_overlay
```

Result: exit `0`. A prior shell `python -c` one-liner aggregation attempt failed
because Markdown backticks were interpreted by the shell; no generated overlay
artifacts were affected, and the dedicated script replaced that attempt.

```bash
./envs/env_CARE/bin/python scripts/evaluation/srr_failure_analysis_overlay.py \
  --case-ids Case1002,Case2002,Case3004,Case3011 \
  --srr-run-dir results/20260704_srr_v25_failure_analysis_overlay/hard_subgroup_runtime/variants/srr_propref_shared_dual_dict \
  --output-dir results/20260704_srr_v25_failure_analysis_overlay/hard_subgroup_overlay \
  --fold 0
```

Result: exit `0`.

```bash
./envs/env_CARE/bin/python scripts/evaluation/srr_help_harm_vs_nnunet.py \
  --srr-metrics results/20260704_srr_v25_failure_analysis_overlay/hard_subgroup_runtime/variants/srr_propref_shared_dual_dict/component_hd_by_case_checkpoint_final.csv \
  --output-dir results/20260704_srr_v25_failure_analysis_overlay/hard_subgroup_help_harm \
  --fold 0
```

Result: exit `0`.

## 关键证据

- hard subgroup cases: `Case1002`, `Case2002`, `Case3004`, `Case3011`
- overlays: 7 scar/edema PNGs listed in `overlay_manifest.md`
- no-T2 safety: `Case1002` edema remains empty, Dice `1.0`, remote FP `0`
- CenterC edema: `Case3004` Dice `0.452563`, HD95 `9.222045`; `Case3011` Dice `0.266909`, HD95 `34.266133`
- CenterC scar: `Case3004` pathology-aware Dice `0.624704`, HD95 `24.000004`; `Case3011` Dice `0.639197`, HD95 `10.959062`
- remote FP: all hard-subgroup SRR rows have remote FP count `0`
- same-split help/harm summary: pathology-aware edema Dice across 4 cases has mean delta `-0.0000599`, scar Dice mean delta `-0.000153`; HD95/remote-FP rows are neutral except tiny scar HD95 deltas
- taxonomy: `Case3011` edema is categorized as `boundary_or_extent_error;crop_or_roi_undercoverage`
- bounded matrix overlays: 42 PNGs across six non-identity variants
- bounded matrix taxonomy: `bounded_matrix_overlay/bounded_matrix_overlay_taxonomy.csv`
  has 96 rows
- no-anchor bounded overlay: `srr_v25_no_anchor` has scar remote-island taxonomy
  in all 8 scar rows and edema remote-island taxonomy in 6 of 8 edema rows

## Gate Decision

decision: `HARD_SUBGROUP_AND_BOUNDED_MATRIX_OVERLAYS_VERIFIED_NEEDS_FULL_FOLD0_AND_AUDIT`

This task now covers a small hard-subgroup smoke packet and the 8-row bounded
matrix overlay/taxonomy pass, but it still does not authorize route promotion,
scientific stop, fold expansion, validation packaging, or upload. The next
required evidence is full fold0 subgroup metrics and a final read-only audit,
plus spatial proposal/dictionary maps if mechanism attribution remains
ambiguous.

No validation package, external upload, git commit, or git push was performed.
