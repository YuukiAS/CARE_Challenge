# SRR-v3 Interface Contract

status: `M0_READY_FOR_REVIEW`

## MyoPS Model Inputs

| input | required content | required provenance |
| --- | --- | --- |
| image tensor | available modalities with availability mask | case id, modality availability, preprocessing geometry |
| nnU-Net anchor probabilities/logits | same-case, same-fold anchor context | anchor fold, checkpoint, prediction/probability path |
| nnU-Net hard prediction | compact-label hard segmentation | decode/export mapping and same-split source |
| anchor uncertainty | entropy, margin, or confidence proxy | computed from anchor probabilities/logits |
| component context | scar/edema/anatomy component features where available | component extraction code path and label semantics |
| prototype bank | train/OOF scar and T2-present edema positive/negative features | selected case ids, split policy, feature stage |
| semantic dictionary metadata | slot task, modality, slot kind, valid mask | runtime CSV/JSON export |

## MyoPS Model Outputs

| output | required content | consumer |
| --- | --- | --- |
| `final_logits` or equivalent probabilities | baseline-preserving bounded correction output | decode/export and metrics |
| `nnunet_anchor_logits` | aligned anchor logits used for final mixture | gate/residual audit |
| `baseline_residual_gate` | gate tensor by voxel/class or equivalent | M1 instrumentation and M2 safety tests |
| `bounded_delta_srr` | bounded SRR delta before gate multiplication | M1 instrumentation |
| `baseline_residual_magnitude` | `abs(gate * bounded_delta)` summary tensor | M1 metrics |
| prototype diagnostics | scar/edema positive/negative counts and source | M1/M2 prototype gates |
| proposal diagnostics | proposal recall/precision and lesion-wise recall | M2/M4 proposal/refinement gates |
| no-T2 safety diagnostics | edema blocked status through loss/logit/decode/export | M1/M2 no-T2 gates |

## Alignment Rules

- Anchor and SRR tensors must share case id, fold, spatial shape, compact labels, and geometry before mixing.
- If anchor probabilities/logits are absent, the route is diagnostic only unless the task explicitly defines a no-anchor ablation.
- Closed-gate behavior must exactly reproduce the same-split nnU-Net hard output within the declared decode path.
- Every exported prediction directory must encode checkpoint/config identity to avoid stale cache reuse.

## Runtime-Active Module Rules

A module is runtime-active only when it is called by the formal runner or exported eval helper and has at least one runtime artifact proving use. Source presence alone is `code_path_exists`, not implementation completion.

| module | runtime-active evidence |
| --- | --- |
| prototype bank | non-empty bank source summary with T2-present edema positive/negative coverage when edema is evaluated |
| dictionary retrieval | slot usage rows with task/family metadata and valid fractions |
| proposal decoder | proposal PR/lesion-recall rows by class |
| local refiner | bounded crop or ROI rows by class/case, not full-volume-only fallback |
| residual gate | gate and residual distributions exported by case/class |
