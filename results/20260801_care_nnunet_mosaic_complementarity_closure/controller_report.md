# Controller report

这轮闭合的实际结论是：nnU-Net 仍然是可靠底线；MoSAIC clean OOF 在 scar 少数病例上有互补信号，但 pure edema 没有形成公平 OOF 互补，M10 只能解释 full-data 机制，不能当泛化证据。当前不授权训练、调阈值、病例级 selector、validation upload 或 Docker upload。

```text
controller_verification_decision: VERIFIED_COMPLETE
strict_validator_status: PASS
terminal_decision: LIMITED_COMPLEMENTARITY_FOR_DIAGNOSTIC_REVIEW_ONLY
```

## Evidence

- 220-case fair OOF matrix: `oof_complementarity_casewise.csv`
- 80-case M10 diagnostic: `m10_diagnostic_casewise.csv`
- 15-case fresh validation no-GT disagreement: `validation_disagreement_casewise.csv`
- Hard-case index: `hard_case_bucket_index.csv`
- Validator: `strict_validator_report.json`

## Main numbers

- Scar all-case: nnU-Net mean Dice 0.561047, MoSAIC mean Dice 0.378168, case-oracle gain 0.021954, MoSAIC rescue fraction 18/220 = 0.081818.
- Pure edema T2-present 80-case: nnU-Net mean Dice 0.430812, MoSAIC mean Dice 0.052756, case-oracle gain 0.002293, MoSAIC rescue fraction 0/80.
- Validation 15-case no-GT disagreement: reused frozen 2026-07-28 fresh outputs; no new GPU job was submitted.

## Boundary

Case-oracle rows are upper bounds only, not a deployable selector. M10 rows are marked `trained_on_case_possible=true` and `not_valid_for_generalization_claim=true`. Validation rows are pairwise agreement only because no GT was used.
