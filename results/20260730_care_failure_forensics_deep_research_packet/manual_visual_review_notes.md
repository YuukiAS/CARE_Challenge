# Manual visual review notes

Generated 20 case montages for Codex visual review. Red marks scar, cyan marks pure edema, yellow marks nnU-Net/MoSAIC disagreement. The `visual_review_status` values in `case_montage_manifest.csv` are updated after image inspection.

## Codex visual review 2026-07-30

Reviewed `case_montages/contact_sheet_20_cases.png` with the local image viewer. All 20 selected case montages are visible: LGE background, GT overlay, nnU-Net OOF overlay, MoSAIC clean OOF overlay, and yellow model-disagreement panel render correctly. The sheet supports qualitative review of large lesion slices and model disagreement, but it is not a substitute for numeric Dice/HD95 tables. Small title text is readable at high zoom; individual case PNGs are available under `case_montages/` for PDF readers who need larger per-case inspection.
