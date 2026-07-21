# Batch7 Repair Controller Bootstrap Snapshot

Snapshot time: `2026-07-21T10:54:17-0400`

The repair is bound to `/users/a/e/aereinh/CARE` on `main`. The task prompt named source main `4c79554de785030ed59081ce3ae233711efc062a`; the actual working HEAD at bootstrap is `63973de4b447fcfba7f0a92f48da1b26c4b85e72`, which includes later local main commits that authorize and normalize the Batch7 repair entrypoint. This snapshot records the actual HEAD and does not revert prior main commits.

Fixed contract evidence:

- Batch7 step300 checkpoint: `results/20260721_srr_batch7_upstream_candidate_quality/runtime/attempts/batch7_formal300_htzhulab_59789651/variants/batch7_formal300_htzhulab_59789651/checkpoints/fold_0/propref_config/checkpoint_validation_step_300.pt`
- Batch7 step300 checkpoint SHA256: `d34ad65890cbb6a12aac3fc35bcab71709d680bff5a3aae2d93e010db1cc0e0d`
- Split file SHA256: `6165caeb5b47feb0d24f20380898037b7e6cead4db1eeba398a3c5a57faf9a1b`
- Fold0 case counts: `176` train, `44` validation
- Runtime mode: `anchor_bounded_srr_correction`
- Decode rule: `outputs["logits"].argmax`
- Repair optimizer steps completed at bootstrap: `0`
- Repair Slurm jobs submitted at bootstrap: `0`

No Batch8, monolithic 1200-step continuation, fold expansion, Cine, validation packaging/upload, hosted metric claim, route promotion, M11, or push is authorized.
