# DEEP RESEARCH MODEL DESIGN INPUT 20260730 V4

This file is a design-input constraint packet, not a new model design. It records what the next Deep Research design may and may not use from the failure-forensics evidence.

## Current readiness

- scientific_evidence_status: `SUFFICIENT`
- deep_research_readiness: `READY`
- current_model_status: `FAILED_GATE`

## Current strong baselines and data truth

- Total MyoPS training cases: 220.
- T2-present official pure-edema denominator: 80.
- C0-present cases: 104.
- nnU-Net clean and MoSAIC clean remain baseline/context evidence; PRISM W3 failed the outer gate and must not be promoted.

## Historical experience allowed as inputs

- Batch7: `pathology-specific proposal/refiner` -> RETEST_WITH_DIFFERENT_IMPLEMENTATION; use only with precondition `isolated patient-held-out causal ablation`.
- MMRD: `reliable-label no-T2 mask` -> RETAIN_AS_DATA_RULE; use only with precondition `T2-present split accounting`.
- ARC: `single encoder with explicit modality gates` -> RETAIN_AS_SAFETY_RULE; use only with precondition `restore decoder capability before claiming gain`.

## Must not repeat

- Do not stack multiple complete backbones as the central method.
- Do not use encoder-only inheritance or decoder reset as a full decoder.
- Do not let nnU-Net or MoSAIC be the only final authority.
- Do not use identical scar and edema heads.
- Do not treat no-T2 cases as pure-edema negatives.
- Do not claim prototype value from unisolated control tensors.
- Do not use weak correction around an anchor without an error selector.
- Do not leave proposal/refiner wiring or component definitions for Codex/controller to invent.
- Do not treat gradient/nonzero-delta validators as causal mechanism proof.

## Large-gain boundary

- scar: case oracle=0.02195407548910211, voxel oracle=0.23751872769841142, conclusion=`ONLY_MODEST_GAIN`.
- pure_edema: case oracle=0.002292654276233319, voxel oracle=0.17295548404011052, conclusion=`ONLY_MODEST_GAIN`.

## Open requirements before READY
