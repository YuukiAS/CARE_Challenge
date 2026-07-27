# CARE-SER-Lite Target-Domain Submission Amendment

**Task:** `20260727_care_ser_lite_owned_final_candidate`  
**Status:** `READY_FOR_CONTROLLER`  
**Precedence:** This amendment overrides conflicting selection, pass/fail, prioritization and terminal-output wording in:

1. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_controller.md`
2. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_executor_plan.yaml`
3. `prompts/tasks/20260727_care_ser_lite_owned_final_candidate_codex_goal.md`

Non-conflicting requirements remain binding.

## 1. Correct scientific estimand

The user confirms that the official MyoPS validation and expected test target are complete `C0+LGE+T2` cases. Therefore two estimands must be separated:

```text
general_robustness_estimand: all 220 mixed-modality OOF cases
target_competition_estimand: 80 complete C0+LGE+T2 OOF cases
```

The existing leakage-safe OOF protocol is fair for estimating each model on the mixed training distribution. It is not sufficient as the sole selection criterion for a deployment target consisting of complete tri-modal cases. This amendment does not discard all-220 evidence; it changes its role from primary promotion gate to robustness/limitation evidence.

This is not post-hoc cherry-picking: modality composition is fixed by the official target before model selection. All reports must show both estimands.

## 2. Historical target-matched evidence that must be frozen

On the exact fold0 complete-trimodal 16-case subgroup, the canonical evaluator records:

```text
nnU-Net scar Dice 0.6933346102, HD95 9.2672235350, exact HD 22.6355255007
Batch7 scar Dice 0.6854888013, HD95 9.2834082672, exact HD 22.2758042341
SCR-R1 control scar Dice 0.6860325888, HD95 9.2597683921, exact HD 25.7235180651
MMRD scar Dice 0.6550156224, HD95 14.2688255933, exact HD 24.3799637552

nnU-Net pure-edema Dice 0.3944358977, HD95 20.0115363661, exact HD 29.6088873174
Batch7 pure-edema Dice 0.3957785770, HD95 19.7929202503, exact HD 29.6267382854
SCR-R1 control pure-edema Dice 0.4012773405, HD95 18.0264648474, exact HD 31.5534569667
MMRD pure-edema Dice 0.3762172836, HD95 21.4019319207, exact HD 29.5672365845
```

Interpretation:

- Batch7 and SCR-R1 scar are target-matched near-ties, not evidence of universal superiority.
- SCR-R1 edema has positive target-matched Dice/HD95 signal but an exact-HD risk.
- MMRD should contribute reliable-label semantics and frozen evidence, not serve as the default final pathology mask.
- These are fold0 secondary diagnostics and justify a validation-domain experiment; they are not five-fold paper claims.

## 3. Revised objective

The task must produce a CARE-owned model suitable for one exploratory validation submission. It must not wait for a universal all-220 win when the official target is complete tri-modal.

Primary architecture is fixed as `CARE-SER-TD-Scar`:

```text
5-fold nnU-Net probability/anatomy anchor
+ MoSAIC raw scar proposals
+ nnU-Net permissive scar proposals
+ available Batch7/SRR proposal evidence
+ CARE-MMRD frozen feature/evidence
+ CARE-owned positive/negative retrieval margin
+ CARE-owned suppress/recover component gate
+ Cascade-style bounded correction and exact pathology fallback
```

MoSAIC and nnU-Net remain evidence sources. The final scar mask must be changed by the CARE gate on at least one held-out and one validation case. A pure external hybrid is forbidden.

Secondary architecture is `CARE-Cascade-TD` and is allowed only if the component gate cannot activate safely or if it offers a clearly distinct second validation candidate:

```text
5-fold nnU-Net anchor
+ existing shallow independent scar/edema correction architecture
+ modality availability
+ T2-reliable edema supervision
+ CARE-MMRD evidence
+ zero-vs-real SRR retrieval matched control
+ complete-trimodal-weighted full-data training
+ bounded pathology correction
```

Do not restore full SRR-v3, dictionaries, SIP, a large ErrorNet, a new backbone or shared scar/edema head.

## 4. Target-aligned data and training

### 4.1 OOF selector training

Use all 220 leakage-safe OOF cases to learn candidate-error relationships. Candidate generation remains GT-blind. Nested CV remains case/fold grouped.

For loss, utility aggregation and inner-CV selection, run both:

```text
U0: uniform all-220
U1: complete-trimodal weight=4, other cases weight=1
```

The target-domain candidate uses U1 only when complete-trimodal held-out metrics improve without catastrophic all-case harm. U0 remains the robustness control.

### 4.2 Final deployment fit

After OOF structure, feature groups, hyperparameters and thresholds are frozen, fit the final CARE gate on all 220 OOF components with the selected U0/U1 weighting. Full-data nnU-Net/MoSAIC/CARE evidence may then be used only for validation inference.

If `CARE-Cascade-TD` is executed, train exactly two matched full-data variants from the same saved initial state and schedule:

```text
C0: target-weighted cascade control, retrieval channels zero
C1: target-weighted cascade SRR, real positive/negative retrieval channels
```

Use complete-trimodal weight=4 and other cases weight=1; no-T2 edema loss weight=0. C0 and C1 must otherwise share initialization, optimizer, augmentation, budget, decode and evaluator. Short substitutes receive zero credit.

## 5. Two separate gates: paper evidence and exploratory validation

### 5.1 Paper-ready scientific gate

A pathology is locally paper-ready only when complete-trimodal five-fold OOF satisfies:

```text
Dice gain >= +0.005 over nnU-Net
HD95 <= 1.05 * nnU-Net
no catastrophic exact-HD outlier
remote FP non-increased
help cases > harm cases
non-zero CARE action
```

All-220 results must also be reported and discussed as robustness evidence, but missing-modality weakness does not invalidate a target-specific claim when target composition is pre-specified.

### 5.2 Exploratory validation gate

A CARE-owned candidate may occupy one validation submission even if it is not yet paper-ready, when complete-trimodal OOF satisfies:

```text
Dice delta >= -0.010 versus nnU-Net
HD95 <= 1.05 * nnU-Net
exact-HD 95th percentile increase <= 5 mm and no new infinite case
remote FP increase <= 10%
help cases >= harm cases - 1
non-zero suppress and/or recover
mechanism output differs from pure nnU-Net and pure MoSAIC
```

All-220 Dice is reported but is not a hard blocker unless there is catastrophic harm, label/geometry failure or mechanism collapse. The candidate must be labeled `EXPLORATORY_TARGET_DOMAIN_VALIDATION_CANDIDATE`, not locally superior.

This gate is justified by the observed MoSAIC rank reversal and the target-matched Batch7/SCR near-ties. It is not permission to tune using hosted scores.

## 6. Execution priority

The Controller must prioritize a real validation candidate over exhaustive optional research:

```text
P0 evaluator parity and asset binding
P1 complete-trimodal reanalysis of nnU-Net, MoSAIC, Batch7, MMRD and SCR
P2 scar candidate dataset + CARE retrieval + suppress/recover gate
P3 nested OOF complete-trimodal target gate
P4 final full-data CARE gate + validation inference + local package
P5 edema/Cascade-TD only if P0-P4 are secure and allocation time remains
P6 validators, Mapper, CURRENT/wiki and local commit
```

Scar-first packaging must not be blocked by an unfinished edema research branch. If scar passes the exploratory gate and edema does not, generate:

```text
CARE-SER-TD-Scar
CARE scar + nnU-Net edema
```

This is a valid CARE-owned candidate because the scar mask is controlled by a trained CARE mechanism.

## 7. Required candidate ladder

The same complete-trimodal evaluator must report:

```text
T0 nnU-Net identity control
T1 historical Batch7 fold0 diagnostic
T2 historical SCR-R1 fold0 diagnostic
T3 CARE base suppress/recover without retrieval or MMRD evidence
T4 T3 + real SRR positive/negative retrieval
T5 T3 + CARE-MMRD frozen evidence
T6 T3 + SRR retrieval + CARE-MMRD evidence
T7 T6 + available historical Batch7/Cascade features
```

Only T3-T7 are CARE-owned candidates. Selection must show which inherited component provides incremental final-mask value.

## 8. Validation output policy

If at least one T3-T7 variant passes the exploratory gate, generate one primary upload-ready package and, only when scientifically distinct and time permits, one secondary package:

```text
primary: CARE-SER-TD-Scar using the best frozen CARE gate
secondary: CARE-Cascade-TD or alternate CF/FD proposal source through the same CARE gate
```

Do not upload automatically. Do not create a pure nnU-Net, pure MoSAIC or deterministic external hybrid package.

If no CARE candidate passes the exploratory gate, return:

```text
NO_CARE_TARGET_DOMAIN_CANDIDATE_SAFE_FOR_VALIDATION
```

and explain the exact nearest candidate and failed criterion. Do not overwrite the scientific record with `NNUNET_ONLY_DOCKER` as the user's desired outcome.

## 9. Controller anti-shortcut requirements

The Controller must reject:

- using all-220 alone to terminate a complete-target candidate;
- copying the previous two-line candidate table;
- using component F1 instead of reconstructed masks;
- treating fold0 target near-tie as five-fold proof;
- claiming complete-target superiority without complete80 OOF;
- skipping validation package after the exploratory gate passes;
- blocking scar packaging because edema did not finish;
- substituting pure external models after a CARE branch fails;
- stopping at the first repairable implementation error.

`VERIFIED_COMPLETE` requires real candidate rows, real final-mask metrics, non-zero CARE mechanism activation, target-aligned decision, package audit when eligible, strict validators and local lightweight commit. Runtime roles must not push.