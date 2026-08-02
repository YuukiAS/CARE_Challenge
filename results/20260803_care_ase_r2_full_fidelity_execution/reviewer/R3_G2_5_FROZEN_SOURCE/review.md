# R3_G2_5_FROZEN_SOURCE Review

Decision: PASS_CONTINUE

Reviewer session: 019fc386-dba4-7b72-a29f-06a657b4fc5f

Candidate commit: 207f360f22dd4e28fcecd4a22b67ed1af074ab42

Effective contract SHA256: b3ea5986b7a2458f758f7353ab023cea85a9cb67a6fb7c7bf12e5bc10e61d09c

## Checks

- Detached checkout HEAD is `207f360f22dd4e28fcecd4a22b67ed1af074ab42`.
- `git ls-remote --heads origin main` reports `207f360f22dd4e28fcecd4a22b67ed1af074ab42 refs/heads/main`.
- Formal wrapper `jobs/care_ase_r2/run_fold_chunk_htzhulab.sh` binds formal execution to `EXPECTED_TRAINING_SOURCE_SHA` and invokes the exact Python entrypoint `scripts/training/care_ase/run_care_ase_r2_chunk.py`.
- The entrypoint imports and uses the candidate checkout implementations for model construction, actual-train area references, deterministic sampler, loss, optimizer, scheduler, checkpoint save/resume, and fixed decode.
- The evaluator path is `scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py`; it fail-closes before W4.5 unless `--allow-after-w45` is present and `preouter_snapshot_push_receipt.json` is PASS/push-verified, then loads checkpoints through `load_care_ase_checkpoint`, performs sliding-window logits, and decodes with `decode_care_ase_r2_logits`.
- G1 evidence is PASS. `known_bad_validator_report.json` contains 31 fixtures, all with nonzero validator exits and `REJECTED_AS_EXPECTED`.
- G2 evidence is PASS with 16/16 pass conditions. The receipt includes module-off/final-logit/final-label evidence and `outer_access_count_before_freeze: 0`.
- Latest R1 and R2 continuous reviewer receipts are `PASS_CONTINUE`.
- `training_source_commit_receipt.json` states `local_head_sha == origin_main_sha == 207f360f22dd4e28fcecd4a22b67ed1af074ab42` and explicitly notes the receipt is post-verification evidence, not part of frozen source.
- No checkpoint, NIfTI, raw data, or large log payload is required for R3 PASS. The review used source hashes and lightweight receipt evidence.

No findings.
