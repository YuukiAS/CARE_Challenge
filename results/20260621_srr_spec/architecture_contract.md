# Architecture Contract: SRR-MyoPS-Lite

Status: `frozen_for_minimal_fold0`

## Method Claim

Result4 is adopted as a segmentation-native selective representation retrieval story: each MyoPS case retrieves dense features from shared and modality-private representation blocks using the current availability vector plus image feature summary. Missing modalities are closed by masks, scar remains LGE-preserving, edema is supervised only when T2 is present, and anatomy is a soft prior rather than a hard deletion rule. The first pass does not use center ID at inference and does not enable alignment.

## Minimal Trainable Version

- Dataset501 input order is `LGE,T2,C0`; availability uses the same order.
- Three modality-specific stems feed a shared/private retrieval bank.
- The minimal bank has one shared expert and one private expert per modality; unavailable private experts receive zero router weight.
- Router input is `[masked_feature_summary, availability_embedding]`.
- Three target routes are produced: anatomy, scar, edema.
- Heads are separate: anatomy logits for `0..3`, scar binary logit for compact `5`, edema binary logit for compact `4`.
- T2-masked edema loss is zero for no-T2 cases. These cases still train scar and anatomy.
- Scar has an LGE-only fallback because LGE is the reference modality and remains valid in all real MyoPS groups.
- The SIP/R2/BR2 idea is implemented as soft entropy plus usage coverage/load-balancing metrics, not as the original discrete support penalty.
- Optional alignment and interaction dictionaries are postponed to later ablations.

## Data And Supervision Matrix

| group | valid encoders | scar loss | edema loss | anatomy loss | modality dropout |
| --- | --- | --- | --- | --- | --- |
| `C0+LGE+T2` | LGE, T2, C0 | yes | weight `1.0` | yes | may drop C0/T2 while preserving LGE |
| `C0+LGE` | LGE, C0 | yes | `0.0` | yes | may drop C0 |
| `LGE-only` | LGE | yes | `0.0` | yes | no synthetic no-LGE case |

Disallowed combinations: no-LGE synthetic training samples, no-T2 edema hard negatives, unmasked zero-filled missing modality features, and center-ID-dependent inference.

## Loss

`L = L_anatomy + L_scar + L_edema + 0.1 * L_prior + L_retrieval`

- `L_anatomy`: cross-entropy over anatomy logits with pathology labels mapped to myocardium-union for the soft anatomy prior.
- `L_scar`: binary Dice+BCE on compact label `5`, all cases.
- `L_edema`: binary Dice+BCE on compact label `4`, only where `T2_present=1`.
- `L_retrieval`: entropy plus coverage/load-balancing regularizer to prevent gate collapse and expert starvation.
- `L_prior`: soft containment pressure for scar/edema outside anatomy union; no hard deletion.

## Fallbacks

- LGE-only scar route remains trainable and produces gradients.
- No-T2 cases provide no dense edema hard-negative loss.
- If sparse routing collapses, the model can be reduced to deterministic availability-aware late fusion using the same stems and heads.
- Fold0 artifacts must be task-, variant-, fold-, checkpoint-, and config-scoped.

## Gate

The spec implementation and tests are sufficient to enter `20260621_srr_fold0`: `GO_FOLD0`.
