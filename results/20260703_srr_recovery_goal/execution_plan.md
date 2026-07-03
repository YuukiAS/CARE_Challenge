# Execution Plan: 20260703_srr_recovery_goal

status: EXECUTOR_RUNNING
controller_task: prompts/tasks/20260703_srr_recovery_goal.md
created_utc: 2026-07-03T14:46:37Z

## Scope

Run the GPT-authored SRR recovery controller task without validation upload,
upload-ready packaging, fold expansion, label/evaluator/fold split changes, or
old SRR-v2 tuning routes.

## Required Gates

- Apply `prompts/EXPERIMENT_ADEQUACY_GATE.md` before any route-promotion or
  route-negative conclusion.
- Apply `prompts/DIAGNOSTIC_PUBLICATION_GATE.md` before any diagnostic-only
  commit/push.
- Treat prior `STOP_NO_PROPREF_SIGNAL` as unsupported unless experiment
  adequacy and route-negative gates pass under independent audit.

## Subagent Sequence

1. `20260703_srr_failure_audit`
   - Executor subagent: launched.
   - Auditor subagent: launch only after executor writes result artifacts.
   - Gate: reviewed adequacy diagnosis is required before SRR repair.
2. `20260703_srr_propref_repair`
   - Launch only after failure audit review exists.
   - Primary route for this controller.
3. `20260703_nnunet_oof_component`
   - May proceed after failure audit review if it does not block primary SRR
     repair.
4. `20260703_anchor_refine_learned`
   - Launch only if reviewed prerequisite evidence from SRR repair or OOF
     component scorer exists.
   - If prerequisites are missing, write `NEEDS_EVIDENCE` instead of a
     deterministic postprocess stop.

## Running Sessions

- failure audit executor: `019f2872-06d0-7c40-a0e6-be47a65d50ef`
- failure audit auditor: `019f2878-27b6-7442-b572-343c6ccb13ec`
- SRR PropRef repair executor: `019f287c-baca-7602-8fd1-f4e4499126d6`
- nnU-Net OOF component executor: `019f287d-125d-7673-a39e-ece4888a7aa4`
- SRR PropRef repair auditor: `019f288d-1cd4-7122-9746-640a58ebab32`
- nnU-Net OOF component auditor: `019f288f-8d6b-7691-a106-475c9dc5ebb8`
- learned anchor refine executor: `019f2894-6928-7920-b833-77855316f735`

## Completed Gates

- Failure audit executor wrote `results/20260703_srr_failure_audit/result.md`
  and required audit packet artifacts.
- Failure audit auditor wrote `results/20260703_srr_failure_audit/review.md`.
- Failure audit decision: `experiment_adequacy_decision=FAIL`,
  `route_negative_decision=STOP_NOT_SUPPORTED`,
  `scientific_resolution_status=SCIENTIFIC_UNDERTRAINED`,
  `recommended_next_state=NEEDS_REVISION`.
- SRR repair may proceed only as bounded repair; no route promotion,
  validation packaging/upload, fold expansion, hosted metric claim, or broad
  next-stage training is authorized.
- SRR repair executor completed with `experiment_adequacy_decision=FAIL`,
  `route_negative_decision=STOP_NOT_SUPPORTED`, and
  `scientific_resolution_status=SCIENTIFIC_UNDERTRAINED`; independent audit is
  pending.
- nnU-Net OOF component executor completed with
  `experiment_adequacy_decision=PASS`, `route_promotion_decision=NO_PROMOTION`,
  and `scientific_resolution_status=SCIENTIFIC_UNRESOLVED`; independent audit
  supported diagnostic publication but no route promotion.
- Learned anchor refine executor was launched only to assess reviewed
  prerequisites and write `NEEDS_EVIDENCE` if inputs are insufficient; no
  learned training is authorized unless the executor finds explicit reviewed
  usable inputs.

## Blocked Actions

- validation packaging
- validation upload
- upload-ready package generation
- fold expansion
- hosted metric claims
- label/evaluator/fold split changes
- old SRR-v2 tuning routes
- next-stage training outside the approved subtasks
