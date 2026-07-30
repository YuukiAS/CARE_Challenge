# Batch7 reusable experience

Batch7 is bound to 968 casewise rows and 410 gradient-authority rows. It should be mined for constraints, not copied as an implementation.

## RETAIN_WITH_DIRECT_EVIDENCE
- Pathology-specific candidate supervision produced measurable final-mask deltas, so future designs may keep direct, casewise intervention accounting.

## RETAIN_AS_DATA_RULE
- Scar and edema must stay separately measured; no-T2 edema cannot be used as a default negative target.

## RETAIN_AS_SAFETY_RULE
- Help/harm and remote-FP accounting are required safety gates; observed help/harm counts were {'harm': 27, 'help': 25, 'neutral': 7}.

## RETEST_WITH_DIFFERENT_IMPLEMENTATION
- Mean non-anchor deltas were scar=-0.036915 and edema=-0.006767, so the idea needs a cleaner implementation before reuse.

## DO_NOT_REUSE_IMPLEMENTATION
- Do not repeat module-present-but-not-final-output designs or near-zero refiner-minus-proposal gains as if they were deployable mechanisms.

## UNRESOLVED
- Prototype routing still needs isolated, patient-held-out evidence before any prototype-specific conclusion is valid.

Proposal/refiner evidence source rows: 2.
