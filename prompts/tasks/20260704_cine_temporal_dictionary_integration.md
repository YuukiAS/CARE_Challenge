---
task_key: "20260704_cine_temporal_dictionary_integration"
project: "CARE_Challenge"
status: "READY_FOR_USER_REVIEW"
task_type: "execution"
risk_level: "high"
allow_code_change: true
allow_shell_command: true
allow_network: true
allow_external_upload: false
review_required: true
mechanism_class: "Cine registration-aware temporal representation dictionary / anatomy-first aggregation"
required_evidence: ["code_diff", "registration_input_contract", "temporal_dictionary", "frame_quality_router", "temporal_aggregation_metrics", "unit_tests"]
forbidden_substitutes: ["frame0 only", "keyframe concat without registration", "temporal descriptor table only", "no frame-quality router", "no myocardium proxy metric", "claiming CineMyoPS from single-frame wrapper"]
---

# Task: Cine Temporal Representation Dictionary Integration

## Goal

Implement the Cine branch shown in SRR-v2/v2.5 as a serious secondary line: ED anchor plus selected keyframes, reference-frame registration/warping, temporal representation dictionary, frame-quality/motion-saliency router, frame-wise anatomy prior, and temporal aggregation for `myocardium_cinemyops` diagnostics.

## Required Work

After `20260704_cine_full_cinema_registration.md` produces a registration option matrix, implement or document blockers for:

- ED/reference frame selection and keyframe selection;
- classical or learning-based registration/warping into reference space;
- frame-wise anatomy prior using CineMA, CorSeg, internal anatomy model, or documented equivalent;
- temporal dictionary slots for ED anchor, registered keyframe texture, anatomy prior, and motion/warp cues;
- frame-quality and motion-saliency router;
- temporal aggregation that is not single-frame fallback;
- comparison against frame0/reference-only baseline.

## Required Tests

- Temporal order and shape sanity for 4D cine inputs.
- Registration warp sanity and folding/Jacobian proxy if deformation fields are available.
- Frame-quality router non-constant test.
- Frame0 identity baseline must be reproduced by closed temporal gate.
- Temporal aggregation must change predictions on at least a documented subset; otherwise mark `PASS_DIAGNOSTIC_NO_TEMPORAL_GAIN`.

## Required Metrics

Report myocardium proxy Dice, component count, temporal consistency, frame-to-frame jitter, warp sanity, runtime, and comparison against frame0 reference. Do not claim hosted `myocardium_cinemyops` improvement unless hosted evidence exists.

## Required Outputs

Write `results/20260704_cine_temporal_dictionary_integration/` with:

- `result.md`
- `temporal_input_contract.md`
- `registration_used.md`
- `temporal_dictionary_contract.md`
- `frame_quality_router.csv`
- `temporal_metrics_summary.md`
- `unit_test_report.md`
- `MANIFEST.md`

## Completion Gate

Do not mark full `PASS` if the output is frame0-only, keyframe-concat-only, or registration-free. Use `PASS_DIAGNOSTIC_WITH_REGISTRATION_GAP` when registration remains unresolved.
