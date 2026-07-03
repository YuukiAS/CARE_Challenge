# Anatomy Prior Adapter Audit

- local CineMA repo path: `results/cinema_adapter/external/CineMA`
- repo exists: `True`
- LICENSE exists: `True`
- README exists: `True`
- license observed: `MIT License`
- provenance caveat: adapter run info was generated in an earlier run and records an `/overflow/htzhu/CARE/...` path; this task did not refresh or download external weights.
- adapter role in this task: frozen local anatomy prior for myocardium/LV proxy only; no scar/pathology head.

## Prior Adapter Run Info

```json
{
  "cinema_label_semantics": {
    "0": "background",
    "1": "RV",
    "2": "myocardium",
    "3": "LV"
  },
  "cinema_repo": "/overflow/htzhu/CARE/results/cinema_adapter/external/CineMA",
  "device": "cuda",
  "frame_strategy": "ed_middle_representative",
  "selected_cases": {
    "train": 64,
    "val": 15
  },
  "trained_dataset": "acdc"
}
```
