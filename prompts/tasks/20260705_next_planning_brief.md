# Next Milestone Planning Brief

Use this brief after the handoff hard-gate repair review.

Required input files:

- `results/20260705_handoff_hard_gate_repair/review.md`
- `results/20260705_handoff_hard_gate_repair/current_bad_packet_regression.md`
- `results/20260705_srr_v25_evidence_supplement_audit/result.md`
- `results/20260705_srr_v25_evidence_supplement_audit/missing_evidence_and_next_questions.md`
- `prompts/HANDOFF_GATE_POLICY.md`
- `prompts/GPT_HARD_GATE_PROMPT.md`

If the hard-gate review is not `AUDITED_GO`, do not plan the next model milestone. Return to gate repair.

If the hard-gate review is `AUDITED_GO`, plan the next SRR-v3 work as milestones rather than one large goal. The final ambition remains full SRR-v3 / SRR-ProposeRefine. MyoPS remains the primary line; Cine remains secondary.

First planning output should create an architecture master contract and the first bounded MyoPS implementation milestone. The first milestone should not train full folds, package validation, upload, or claim route promotion. It should close runtime gaps: baseline-preserving anchor/residual safety, strong encoder/context path, pathology proposal/refinement path, real prototype/dictionary runtime evidence, and no-T2 edema safety.

Formal training and Cine temporal integration should be separate later milestones with their own completion checks and reviews.
