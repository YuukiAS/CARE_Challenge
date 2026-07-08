# M9 RRL/BR2 Adaptation Contract

status: `PARTIAL_CODE_REPAIR_NEEDS_RUNTIME_EVIDENCE`

The intended M9 adaptation uses real modality availability rather than imputed fake modalities:

- LGE slots are valid for scar evidence.
- T2 slots are valid only when T2 is available.
- C0 slots are valid only when C0 is available.
- Interaction slots require all modalities in the interaction pair.
- no-T2 myocardium must not be used as edema-negative memory.

Runtime Pattern-SIP, invalid-slot, and prototype-memory evidence remains pending.

