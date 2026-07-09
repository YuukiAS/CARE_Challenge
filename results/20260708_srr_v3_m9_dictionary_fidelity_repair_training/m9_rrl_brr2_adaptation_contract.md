# M9 RRL/BR2 Adaptation Contract

status: `RUNTIME_RECONCILED_FOR_M9_FOLLOWUP`

The intended M9 adaptation uses real modality availability rather than imputed fake modalities:

- LGE slots are valid for scar evidence.
- T2 slots are valid only when T2 is available.
- C0 slots are valid only when C0 is available.
- Interaction slots require all modalities in the interaction pair.
- no-T2 myocardium must not be used as edema-negative memory.

Runtime reconciliation evidence:

- Pattern-SIP usage: `m9_pattern_sip_usage_by_group.csv`, regenerated from terminal M9 runtime roots.
- Invalid-slot mask: `m9_dictionary_invalid_slot_mask_report.csv`, regenerated from terminal M9 runtime roots with runtime rows for the dictionary mask summary.
- Prototype memory: `m9_prototype_memory_summary.json`, reconciled to train/OOF runtime feature sources with non-empty scar/edema positive and safe-negative counts and zero no-T2 myocardium edema-negative contribution.
