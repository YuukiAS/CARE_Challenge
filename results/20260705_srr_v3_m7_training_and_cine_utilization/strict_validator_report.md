# Strict Validator Report

status: `PASS_FAIL_CLOSED`

| known-bad packet | actual status | reason |
| --- | --- | --- |
| all loss gradient rows BACKWARD_FAILED | `PASS_FAIL_CLOSED` | gradient sanity must not be all BACKWARD_FAILED |
| gradient fixed but training-loss validity missing | `PASS_FAIL_CLOSED` | loss graph report exists |
| hard subgroup rows all CenterA/LGE-only/no-T2 | `PASS_FAIL_CLOSED` | continued hard subgroup groups are present |
| diagnostic hardcase rows mixed into formal best-variant decision | `PASS_FAIL_CLOSED` | formal best rows remain formal_val only |
| Cine branch copies M5 evidence without new registration attempt | `PASS_FAIL_CLOSED` | M7 continued Cine repair report exists |
| frame0-only or one-case SyN marked usable registration | `PASS_FAIL_CLOSED` | no frame0/one-case usable registration |
| untrained VoxelMorph marked usable | `PASS_FAIL_CLOSED` | untrained VoxelMorph is not usable |
| temporal dictionary marked ready despite no usable registration | `PASS_FAIL_CLOSED` | temporal dictionary remains blocked without usable registration |
| completion_check says ready while any continued blocker remains | `PASS_FAIL_CLOSED` | ready check requires fixed gradients, subgroup coverage, Cine repair report, and temporal evidence |
