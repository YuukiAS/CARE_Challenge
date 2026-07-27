# CARE-SER Dual-Pathology Target-Domain Submission Amendment

**Task:** `20260727_care_ser_lite_owned_final_candidate`  
**Status:** `READY_FOR_CONTROLLER`  
**Precedence:** This amendment has highest precedence over conflicting wording in:

1. `prompts/tasks/20260727_care_ser_lite_target_domain_submission_amendment.md`
2. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_controller.md`
3. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_executor_plan.yaml`
4. `prompts/tasks/20260727_care_ser_lite_target_domain_codex_goal.md`
5. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_codex_goal.md`

Non-conflicting requirements remain binding.

## 1. User hard requirement: both pathologies must be active

The primary validation candidate must process both scar and edema with separate CARE-owned learned mechanisms. Scar-first packaging with nnU-Net-only edema is no longer an acceptable primary candidate.

Required primary architecture name:

```text
CARE-SER-TD-Dual-v1
```

Required dataflow:

```text
[LGE, T2, C0] + modality availability
  -> frozen 5-fold nnU-Net anatomy/scar/edema anchor, probabilities and uncertainty
  -> frozen final/full-data MoSAIC raw scar proposals only
  -> frozen CARE-MMRD feature/evidence source
  -> CARE scar positive/negative retrieval
  -> CARE ScarSuppress + ScarRecover component gates
  -> CARE edema positive/negative retrieval using T2-present reliable labels only
  -> CARE EdemaSuppress + EdemaRecover zone gates
  -> pathology-specific bounded correction
  -> protected anatomy
  -> scar-priority pure-edema composition
  -> pathology-specific exact identity fallback
```

Both scar and edema branches must:

- be trained or calibrated from leakage-safe OOF evidence;
- use a CARE-owned decision model;
- produce reconstructed final-mask metrics;
- show non-zero held-out mechanism activation;
- show non-zero validation inference activation on at least one case unless the branch correctly chooses identity for every case and the strict validator therefore marks the package ineligible;
- remain independently auditable and independently fail-safe.

MoSAIC edema remains forbidden. No-T2 edema must remain exact nnU-Net identity.

## 2. Final model relative to the two blueprints

The selected system is the target-domain dual-pathology refinement of `CARE-SER-Lite`, not the full dual 3D ErrorNet blueprint.

Retain from `CARE_SER_Lite_revised_blueprint_20260726.md`:

- component-level scar decisions;
- T2-conditioned edema-zone decisions;
- reliable-label/no-T2 semantics;
- protected anatomy;
- zero-correction identity state;
- pathology-specific fallback;
- exact-HD and remote-FP audit.

Strengthen relative to that blueprint:

- edema is mandatory in the primary candidate rather than optional;
- both branches use target-aligned complete-trimodal OOF selection;
- real frozen CARE-MMRD embeddings are required;
- real positive/negative SRR retrieval matched against zero retrieval is required;
- raw/pre-cleanup MoSAIC proposals are used for scar instead of final-largest-component-only masks;
- full-data proposal-source calibration stress is required before validation packaging.

Delete from `CARE_SER_dual_pathology_submission_blueprint_20260726.md`:

- independent four-scale 3D ScarErrorNet and EdemaZoneErrorNet;
- separate FN/FP dense heads and four correction fields;
- a new large backbone;
- large learned arbiters, dictionaries, SIP or deep memory systems.

Reason: one-day submission deadline, small reliable edema population, and prior evidence that average gains were lost through worst-case boundary errors. Low-capacity component/zone decisions are more testable, calibratable and Docker-safe.

## 3. Competition estimand and local gates

Primary selection population:

```text
80 complete C0+LGE+T2 OOF cases
```

Robustness/limitation population:

```text
all 220 mixed-modality OOF cases
```

Both must be reported. Complete-target selection is pre-specified by official validation/test modality composition.

### Scar exploratory validation gate

```text
complete-target Dice delta >= -0.010 versus nnU-Net
HD95 <= 1.05 * nnU-Net
exact-HD 95th percentile increase <= 5 mm and no new infinite case
remote FP increase <= 10%
help cases >= harm cases - 1
non-zero suppress and/or recover
final masks differ from pure nnU-Net and pure MoSAIC
```

### Edema exploratory validation gate

Only T2-present reliable OOF cases enter metric selection:

```text
pure-edema Dice delta >= -0.005 versus nnU-Net
edema-zone Dice delta >= -0.005 versus nnU-Net
HD95 <= 1.05 * nnU-Net
exact-HD 95th percentile increase <= 5 mm and no new infinite case
remote FP increase <= 10%
help cases >= harm cases - 1
no-T2 changed voxels = 0
non-zero suppress and/or recover
```

Paper-ready gate for either pathology remains Dice gain >= +0.005 with non-worse safety metrics. A primary package requires both pathology branches to pass the exploratory gates. If one branch fails, do not generate the primary dual package; repair within scope or report the nearest failed criterion.

## 4. Scar branch

Candidate sources:

```text
nnU-Net argmax and thresholds 0.15/0.20/0.25/0.30
final/full-data MoSAIC raw, pre-containment, pre-cleanup and pre-largest-component thresholds 0.15/0.20/0.25/0.30
available Batch7/SRR scar proposal evidence when exact assets exist
```

CARE features:

```text
nnU-Net probability/uncertainty
MoSAIC probability/source agreement
LGE regional statistics
soft anatomy overlap and distance
morphology and remote-island features
CARE-MMRD frozen embedding
SRR top-5 positive similarity
SRR top-5 negative similarity
positive-minus-negative retrieval margin
```

Actions:

```text
anchor component: retain or suppress
non-anchor proposal: reject or recover
```

## 5. Edema branch

Candidate sources:

```text
nnU-Net edema-zone argmax
nnU-Net edema-zone thresholds 0.15/0.20/0.25/0.30
T2-supported contiguous regions inside soft myocardium shell
available Batch7/SCR edema-region evidence only as a feature/candidate source when exact assets exist
```

CARE features:

```text
nnU-Net zone probability/uncertainty
T2 and LGE regional statistics
soft anatomy overlap and distance
morphology and boundary uncertainty
CARE-MMRD frozen embedding
reliable positive/negative retrieval from T2-present cases only
modality availability
```

Actions:

```text
anchor zone: retain or suppress
non-anchor T2-supported region: reject or recover
```

Final composition:

```text
final_zone = (anchor_zone - accepted_suppress) union accepted_recover
final_pure_edema = final_zone - final_scar
```

A scar-edema subtraction coupling audit is mandatory.

## 6. First and second validation packages

### Submission 1 — primary, highest hosted-score probability

```text
CARE-SER-TD-Dual-FD-v1
```

Composition:

```text
Anatomy: nnU-Net 5-fold identity
Scar proposals: final/full-data MoSAIC raw proposal path
Scar final: CARE ScarSuppress/ScarRecover
Edema proposals: nnU-Net/T2 candidate zones
Edema final: CARE EdemaSuppress/EdemaRecover
Features: real CARE-MMRD + real SRR retrieval
Correction: Cascade-style bounded composition and pathology fallback
Cine: current frozen verified tree
```

Rationale: hosted evidence indicates final/full-data MoSAIC scar proposals are the strongest target-domain proposal source, while CARE remains the final pathology authority. This package is not an nnU-Net/MoSAIC hybrid because both pathology masks are decided and changed by CARE-owned gates.

Package only when both scar and edema exploratory gates pass and FD proposal calibration remains inside the OOF/CF envelope.

### Submission 2 — scientifically distinct CARE candidate

Preferred candidate:

```text
CARE-Cascade-TD-Dual-v1
```

Run only if two matched full-data shallow Cascade variants can finish safely in the existing allocation:

```text
C0: target-weighted control with retrieval channels zero
C1: same initialization/data/optimizer/augmentation/budget/decode with real SRR retrieval
```

Both scar and edema are trained with complete-trimodal weight=4; no-T2 edema loss weight=0; CARE-MMRD evidence is active. Submit C1 only when it passes both pathology exploratory gates and shows incremental final-mask value over C0.

Deterministic fallback for Submission 2 when Cascade cannot finish or fails its matched gate:

```text
CARE-SER-TD-Dual-CF-v1
```

This uses the same frozen CARE gates as Submission 1 but clean five-fold MoSAIC ensemble scar proposals instead of full-data proposals. It remains a CARE-owned dual-pathology system. Generate it only when both pathology gates pass under CF and it is scientifically distinct from Submission 1 by proposal-source hashes and mechanism actions.

Do not replace either submission with pure nnU-Net, pure MoSAIC or their deterministic merge.

## 7. Execution priority under one-day deadline

```text
P0 evaluator parity, assets and complete-target historical reanalysis
P1 dual candidate dataset and CARE-MMRD/SRR evidence
P2 scar and edema nested OOF gates
P3 final dual gate freeze and FD calibration stress
P4 Submission 1 validation inference, two-run equality and local ZIP
P5 matched CARE-Cascade-TD-Dual; if not feasible, CF dual fallback
P6 Submission 2 validation inference, two-run equality and local ZIP
P7 strict validator, Mapper, CURRENT/wiki and local commit
```

Submission 1 packaging must not wait for Submission 2. Edema is blocking for Submission 1, but optional research ablations are not.

## 8. Required terminal answers

The Controller must report:

1. scar and edema target-matched OOF metrics separately;
2. whether SRR retrieval and MMRD evidence independently improve each pathology;
3. whether both CARE branches activate in held-out and validation inference;
4. Submission 1 exact ZIP path and why it is expected to outperform current MoSAIC hosted submission;
5. Submission 2 exact ZIP path or exact reason it was not generated;
6. paper-ready versus exploratory-only status for each pathology;
7. all-220 robustness limitations without using them to erase the pre-specified target-domain result.

Allowed terminal candidate states:

```text
CARE_SER_TD_DUAL_FD_READY_AND_SECOND_CASCADE_READY
CARE_SER_TD_DUAL_FD_READY_AND_SECOND_CF_READY
CARE_SER_TD_DUAL_FD_READY_ONLY
NO_DUAL_CARE_TARGET_DOMAIN_CANDIDATE_SAFE_FOR_VALIDATION
OPERATIONALLY_BLOCKED_EXISTING_ALLOCATION_OR_REQUIRED_ASSET
```

`VERIFIED_COMPLETE` requires real dual-pathology reconstructed masks, real metrics, non-zero CARE actions, package audits when eligible, strict validators, Mapper/CURRENT/wiki update and local lightweight commit. Runtime roles must not push.