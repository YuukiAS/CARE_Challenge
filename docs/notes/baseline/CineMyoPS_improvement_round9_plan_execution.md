# CineMyoPS improvement round9: Lane B hosted/HD plan implementation

Date: 2026-05-20

## Scope

- Planning-to-implementation pass for Lane B CineMyoPS hosted-metric/HD repair.
- No training, no Slurm submission, no long inference, no validation zip creation, no weight download.
- Goal: make the next Codex pass able to implement postprocess diagnostics and one pretrained-backbone smoke test without rereading all notes.

## Files Added

- `docs/plans/laneB_cinemyops_hosted_motion_plan.md`
  - Records the executive decision, wrapper audit, hosted metric hypotheses, short-term repair plan, medium-term motion/pretrained route, candidate screening matrix, phase gates, and next deliverables.
- `scripts/evaluation/cinemyops_component_hd_audit.py`
  - Read-only audit for existing compact-label CineMyoPS prediction directories.
  - Reports per-case and aggregate Dice, HD, HD95, scar components, scar volume, largest-component fraction, removed voxels/components, bbox distance, center distance, and fallback equality checks.
- `scripts/screening/check_cine_pretrained_candidate.py`
  - Metadata-only screening for CineMA, CorSeg-CineSAX, ViTa, StrainNet, MTI-MyoScarSeg, VoxelMorph, SegMorph, cineCMR-SAM, InverseForm, nnU-Net Task114/M&Ms, and the current CineMyoPS paper repo.
  - Does not download weights or run inference.

## Verification

Syntax check:

```bash
./envs/env_CARE/bin/python -m py_compile \
  scripts/evaluation/cinemyops_component_hd_audit.py \
  scripts/screening/check_cine_pretrained_candidate.py
```

Metadata screening:

```bash
./envs/env_CARE/bin/python scripts/screening/check_cine_pretrained_candidate.py \
  --output-dir results/diagnostics/cine_pretrained_screening
```

Outputs:

- `results/diagnostics/cine_pretrained_screening/screening.json`
- `results/diagnostics/cine_pretrained_screening/screening.md`

Component/HD audit:

```bash
./envs/env_CARE/bin/python scripts/evaluation/cinemyops_component_hd_audit.py \
  --pred-dirs \
    pathology_direct=results/predictions/CineMyoPS_R6_pathology_direct/fold_0 \
    lcc=results/predictions/CineMyoPS_R8_hd_repair/pathology_largest_component/fold_0 \
  --baseline-variant pathology_direct \
  --output-prefix results/diagnostics/CineMyoPS_phase0_component_hd
```

Outputs:

- `results/diagnostics/CineMyoPS_phase0_component_hd.csv`
- `results/diagnostics/CineMyoPS_phase0_component_hd.json`
- `results/diagnostics/CineMyoPS_phase0_component_hd.md`

Aggregate result:

| variant | cases | class_1 Dice | class_3 Dice | class_3 HD | class_3 HD95 | scar comps | removed voxels | worst class_3 HD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pathology_direct | 13 | 0.6933 | 0.4378 | 40.4694 | 26.6533 | 5.5385 | 0.0000 | 63.0715 |
| lcc | 13 | 0.6933 | 0.4441 | 27.7648 | 18.7983 | 1.0000 | 222.1538 | 59.6776 |

## Interpretation

This implementation confirms the round8 local conclusion with a reusable diagnostic script: largest-component repair keeps `class_1` unchanged, slightly improves `class_3` Dice, reduces mean scar components to exactly one per case, and improves `class_3` HD/HD95 substantially.

The repair remains a hosted calibration candidate, not a final model. It tests whether hosted `myocardium_cinemyops` is primarily sensitive to raw `2221` pathology topology and HD. If the hosted result remains poor, the next useful work is a `src/` motion/strain/pretrained-cine route rather than more local `class_1` proxy tuning.

## Next Implementation Pass

1. Extend postprocess diagnostics only if hosted LCC result supports the pathology/topology hypothesis.
2. Run metadata/license verification for CineMA and CorSeg-CineSAX before any weight download.
3. If allowed, do one local-weight or explicitly approved one-case pretrained anatomy smoke test; do not train.
4. Keep all candidate conclusions tied to `class_3` scar sanity, HD/HD95, components, raw `2221` label QA, and hosted `myocardium_cinemyops` hypotheses.
