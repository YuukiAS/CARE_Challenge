# Cine Missing Evidence

primary_missing_tokens:

- `CINE_REGISTRATION_GAP_REMAINS`
- `TEMPORAL_DICTIONARY_NOT_READY`

## Missing Or Insufficient Evidence

| requirement | current evidence | decision |
| --- | --- | --- |
| CineMA/anatomy prior | ACDC SAX seed0 adapter ran on 64 train + 15 validation cases; anatomy only | `PARTIAL_SUPPORTED_ANATOMY_ONLY` |
| ANTsPy SyN same-safe-subset matrix | one downsampled `Case1001` smoke | `SMOKE_ONLY_NEEDS_MATRIX` |
| VoxelMorph trained/usable status | local PyTorch API runs, but untrained near-identity | `NOT_TRAINED_NOT_USABLE` |
| SimpleITK/Demons fallback | 8-case fallback improves moving frame but has negative Jacobian/folding evidence | `FALLBACK_ONLY` |
| optical flow | 59-case proxy has temporal signal but poor folding proxy | `PROXY_ONLY` |
| frame0/ED controls | present and necessary | `CONTROL_SUPPORTED` |
| temporal dictionary runtime | contract exists; no runtime dictionary artifact | `TEMPORAL_DICTIONARY_NOT_READY` |
| frame-quality router | input signals exist in prior proxy/fallback rows; no production router integrated | `PROBE_ONLY` |
| hosted metric | not run by task constraint | `NOT_CLAIMED` |
