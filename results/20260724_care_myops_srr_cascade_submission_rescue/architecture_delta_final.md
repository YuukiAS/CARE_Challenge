# SCR-R1 RC1 Architecture Delta Final

- Scope: same-science runtime closure for CARE-SRR-Cascade SCR-R1; not Batch11 and not SCR-R2.
- Implemented runtime paths: anchor cache, source cache, category-aware prototypes, independent pathology trunks, formal trainer/resume, W4 evaluator/selector/aggregator, W6 strict validator.
- No scientific architecture diagram change was required by the repair controller; the runtime state changed from `repair-ready/formal-not-started` to `terminal evaluated baseline fallback`.
- Package path is conditionally skipped because both scar and edema decisions are `FALLBACK_TO_NNUNET`.
- Authorized external actions remain false: upload=false, push=false, fold expansion=false, new Cine training=false.
