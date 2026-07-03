# Metrics Summary

Same-split references from the audited MyoPS evidence package:

- nnU-Net fold0 scar all-case Dice: `0.5602`
- nnU-Net fold0 edema GT-positive Dice: `0.3944`

| variant | scar all-case Dice | edema GT-positive Dice | scar proposal recall | scar proposal precision | edema proposal recall | edema proposal precision | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `srr_propref_shared_dual_dict` | 0.0007 | 0.0070 | 0.1756 | 0.0040 | 0.9985 | 0.0014 | `DIAGNOSTIC_ONLY` |
| `srr_propref_scar_precision` | 0.0011 | 0.0069 | 0.0798 | 0.0043 | 0.6440 | 0.0015 | `DIAGNOSTIC_ONLY` |
| `srr_propref_no_proto_cascade` | 0.0038 | 0.0066 | 0.5582 | 0.0045 | 1.0000 | 0.0014 | `DIAGNOSTIC_ONLY` |

Hosted validation metrics are `evidence not found`; validation upload and packaging are forbidden for this task.
