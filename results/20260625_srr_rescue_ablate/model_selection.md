# Model Selection

status: `SELECT_SRR_RECOVERED`
selected_variant: `best_srr_recovered`

## Basis

- `best_srr_recovered`: edema GT-positive Dice `0.1928`; scar all-case Dice `0.0923`; edema HD95 `97.7248`; scar HD95 `127.0317`.
- `retrieval_no_sip_or_weak_sip`: edema GT-positive Dice `0.1358`; scar all-case Dice `0.0702`; edema HD95 `115.4910`; scar HD95 `129.1230`.
- `best_conditional_control`: edema GT-positive Dice `0.1103`; scar all-case Dice `0.0581`; edema HD95 `138.1377`; scar HD95 `113.4492`.
- `late_fusion_no_dictionary`: edema GT-positive Dice `0.0601`; scar all-case Dice `0.0442`; edema HD95 `129.9965`; scar HD95 `130.5623`.

## Decision Rationale

- Select recovered SRR because it beats the previous conditional anchor, late fusion without dictionary, and weak-SIP retrieval on both primary fold0 pathology Dice comparisons.
- Do not select late fusion: it loses the edema and scar signal and has high component/remote-FP burden.
- Do not select weak-SIP retrieval: weakening SIP did not improve Dice or HD95 relative to the recovered expert-dropout SRR.
- Caveat: all fold0 pathology scores are still low, and recovered SRR still needs a follow-up revision focused on lesion compactness, false positives, and scar/edema localization before fold expansion.
