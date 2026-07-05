# SRR-v3 Architecture Contract

status: `M0_READY_FOR_REVIEW`

## Scope

This contract is the binding M0 architecture story for the next SRR-v3 / SRR-ProposeRefine work. It does not implement model code, train a model, package validation, upload, promote a route, or start M1.

## Source Evidence

- Handoff repair review: `results/20260705_handoff_hard_gate_repair/review.md`, decision `AUDITED_GO`.
- Bad-packet regression: `results/20260705_handoff_hard_gate_repair/current_bad_packet_regression.md`, strict/default validator exits `1` on the known incomplete SRR-v2.5 packet.
- Evidence supplement: `results/20260705_srr_v25_evidence_supplement_audit/result.md`, route decision `DIAGNOSTIC_ONLY_NEEDS_EVIDENCE`.
- Missing evidence list: `results/20260705_srr_v25_evidence_supplement_audit/missing_evidence_and_next_questions.md`.
- Gate rules: `prompts/HANDOFF_GATE_POLICY.md`, `prompts/GPT_HARD_GATE_PROMPT.md`, `prompts/MILESTONE_REVIEW_PROTOCOL.md`.

## Locked Architecture Story

1. nnU-Net is the protected same-split baseline anchor. It supplies probabilities/logits, hard predictions, component context, uncertainty, and anatomy context.
2. SRR remains the scientific branch. It includes availability-aware modality handling, a strong encoder/context path, semantic retrieval dictionary, train/OOF prototype banks, pathology-specific proposal/refinement, and no-T2-safe edema behavior.
3. The final MyoPS prediction is a baseline-preserving bounded correction, not a from-scratch replacement. The allowed form is `final = nnU-Net anchor + gated SRR residual`, or an explicitly equivalent bounded probability/logit mixture.
4. The first scientific question is whether SRR can learn where to open the gate and make bounded helpful corrections on uncertain or wrong nnU-Net regions while preserving already-correct regions.
5. Cine remains secondary. Cine work is diagnostic until there is a same-safe-subset registration/temporal evidence matrix. Cine cannot block MyoPS M1-M4 unless a future user task explicitly changes priority.

## Non-Negotiable Constraints

- Do not treat 6-step bounded smoke checkpoints as formal route evidence.
- Do not treat eval-only full-fold metrics over old checkpoints as adequate training.
- Do not call edema prototype retrieval tested when `edema_positive=0` or `edema_negative=0` in the runtime source summary.
- Do not call a gate/residual mechanism diagnosed when full-eval gate open-rate and bounded-delta statistics are absent.
- Do not let a milestone executor write its own `review.md` or mark `*_AUDITED_GO`.

## Required SRR-v3 Components

| component | required role | minimum evidence before scientific claim |
| --- | --- | --- |
| nnU-Net anchor | protected baseline and context source | exact same-split alignment, anchor confidence/uncertainty, hard prediction and probability/logit provenance |
| residual gate | controls where SRR may modify anchor | gate mean, p95, open-rate thresholds, class/case summaries, closed-gate identity evidence |
| bounded residual | limits correction magnitude | bounded-delta abs mean/p95/max, `gate*delta` summaries, decode label-delta counts |
| strong encoder/context path | SRR feature capacity | realistic-channel or memory-safe evidence; not only tiny `base_channels=4` smoke |
| prototype bank | pathology retrieval memory | train/OOF source, selected case ids, scar and T2-present edema positive/negative counts |
| semantic dictionary | task-aware retrieval | runtime slot usage, task/family metadata, collapse checks, ablation-ready switches |
| proposal/refinement | pathology-local correction | proposal recall/precision, lesion recall, bounded ROI crop evidence, remote-FP and HD95 metrics |
| no-T2 edema policy | prevent unsafe edema inference | loss/proposal/ROI/logit/decode/export safety evidence on no-T2 cases |

## Completion Boundary

M0 is complete only as an executor milestone when all required M0 files exist and `completion_check.md` says `M0_READY_FOR_REVIEW`. M0 does not authorize M1. M1 is blocked until a separate read-only reviewer writes `results/20260705_srr_v3_m0_architecture_master_contract/review.md` containing `M0_AUDITED_GO`.
