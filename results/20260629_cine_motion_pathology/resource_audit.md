# Cine Motion Pathology Resource Audit

- Safe cases: `59`
- Mismatch cases held out: `5`
- Input source: existing CineMA adapter predictions under `results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/`.
- External upload: not used.
- Validation package generation: not used.
- GPU: not used.
- `/overflow` writes: not used. Some historical adapter prediction paths recorded in CSV are symlink/source paths pointing to `/overflow`; they were read-only references.
