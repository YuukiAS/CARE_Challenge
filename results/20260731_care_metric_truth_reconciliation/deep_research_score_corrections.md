# Deep Research score corrections

Deep Research 后续写作可以使用这些修正后的事实，但不能把它们合并成单一“模型高低”表述。

| previous ambiguous use | corrected meaning | allowed future wording |
|---|---|---|
| D0 0.9224 / 0.9231 | stock fold0 nnU-Net on frozen 12-case inner-select, GT Dice | proves evaluator/checkpoint/geometry can reproduce strong inner-select GT Dice; not evidence of clean OOF or hosted validation |
| clean nnU-Net 0.5610 scar / 0.4308 pure edema | local 5-fold clean OOF, 220 scar cases and 80 T2-present pure-edema cases | fair local comparator against MoSAIC clean OOF in the same population |
| MoSAIC clean scar 0.3782 / pure edema 0.0528 | local clean OOF MoSAIC result | shows clean MoSAIC is below nnU-Net under local OOF; do not replace with hosted score |
| MoSAIC M2-M10 high probe rows | full-data train-on-case mechanism decomposition on 80 T2-present cases | can motivate mechanisms, not fair validation, not leaderboard evidence |
| PRISM W3 outer scar/edema-zone | fold0 one-time outer diagnostic after inner checkpoint selection | only compare to same-fold nnU-Net outer comparator; do not use for checkpoint selection or hosted claim |
| hosted MoSAIC 0.6965 scar and companion rows | hidden leaderboard references with partial local provenance | can be cited as hosted reference with unresolved exact package binding |
| edema-zone | internal labels 4 or 5 | never present as official pure edema; official edema is internal label 4 only and T2-present local denominator is 80 |

A0-A3 mechanism experiments may now use this reconciliation as the Lane A metric truth receipt. This task itself still does not train models; Lane B formal training may proceed only under its own task contract and resource gates.

## Late user-supplied Deep Research draft handling

The file `/users/a/e/aereinh/CARE/CARE Myocardium 下一代模型深度研究与设计裁决.md` was added by the user after packet generation began and was read only. It is not moved by this task because the frozen write scope is limited. Its prose includes D0 0.922x in an official-validation/hosted context; this packet rejects that wording and records the occurrence as non-claim-allowed. The corrected machine truth remains: D0 0.922x is inner-select prediction-vs-GT Dice on 12 frozen cases. The draft also contains a hosted nnU-Net anchor prose claim around 0.92/0.923; this packet does not promote that prose claim and instead uses locally bound leaderboard alignment rows as hosted references.
