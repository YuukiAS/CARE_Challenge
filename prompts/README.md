# CARE Prompts

This directory stores reusable prompts and historical execution prompts. Active
project state should live in `README.md`, `TODO.md`, and governed plans under
`docs/plans/`; prompts are source material, not the source of truth.

## Layout

| Path | Purpose |
| --- | --- |
| `Baseline/` | Archived baseline-improvement prompts for MyoPS-Net, U-MyoPS, and CineMyoPS. These are historical inputs for negative evidence and should not be treated as current mainline plans. |
| `LaneA/` | Lane A MyoPS prompt drafts for later rounds. Use the matching `docs/plans/laneA_roundXX_*` file as the controller before executing. |
| `DeepResearch/` | Deep research prompt material and mechanism-source notes. External methods still require license, compliance, input/output, label mapping, and one-case smoke gates before use. |
| `CARE_Challenge_Analysis.md` | General CARE challenge analysis prompt/material. |
| `Baseline_report.md` | Legacy baseline reporting prompt/material. |

## Rules

- Do not execute directly from a prompt if it conflicts with `docs/plans/care_myocardium_plan_registry_rules.md`.
- Do not treat old baseline prompts as authorization to continue patching third-party baselines as the mainline.
- For current CARE Myocardium execution, start from `README.md`, `TODO.md`, and the relevant `docs/plans/` file.
