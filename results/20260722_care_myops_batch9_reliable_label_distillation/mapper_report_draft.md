# Batch9 Mapper Report Draft

本次 mapper 检查确认 Batch9 新直接分割链已经实现并完成固定预算运行，但评价结果不支持保留为可用科学主线。旧 SRR、prototype/memory、proposal/refiner、arbiter/gate、BR2-lite、SIP、Cine、fold expansion 和 upload 仍未授权。

- inspected_model: `src/care_myocardium/models/care_mm_reliable_distill.py::CAREMMReliableDistillResEnc`
- inspected_losses: `src/care_myocardium/losses/care_mm_losses.py::compute_care_mm_loss`
- inspected_training: `scripts/training/run_care_mm_batch9_reliable_distill.py`
- inspected_evaluation: `scripts/evaluation/evaluate_care_mm_batch9.py`, `aggregate_care_mm_batch9.py`, `finalize_care_mm_batch9.py`, `validate_care_mm_batch9_packet.py`
- runtime_evidence: `completion_check.md`, `decision_matrix.csv`, `strict_validator_report.json`, `casewise_metrics.csv`, `subgroup_metrics.csv`
- final_token: `BATCH9_MAINLINE_NO_USABLE_SIGNAL_RETURN_TO_PLANNER`
- code_fingerprint: `care_mm_reliable_distill.py=5db67db7;care_mm_losses.py=eb3f106d;care_mm_batch9.py=265deeb8;run_care_mm_batch9_reliable_distill.py=62ce99f5;evaluate_care_mm_batch9.py=29d2a1a3;aggregate_care_mm_batch9.py=84182a5f;finalize_care_mm_batch9.py=aaf596c9;validate_care_mm_batch9_packet.py=314a31ef;batch9_reliable_label_distillation.yaml=1f240928`
- evidence_fingerprint: `completion_check.md=1938afdb;decision_matrix.csv=8a92950d;strict_validator_report.json=06875958;subgroup_metrics.csv=ac79e318;casewise_metrics.csv=bd03d3de;slurm_formal_chain.json=2bf81b99;slurm_race_events.csv=66b613ff`

Component deltas:

- Batch9 direct ResEnc components are implemented and evaluated, but terminal evidence is negative/no usable signal.
- Batch8 remains superseded and unexecuted.
- Historical SRR/prototype/refiner/gate components remain provenance only and have zero Batch9 call authority.
- Mapper/wiki observability updated in `wiki/README.md`, `wiki/current_state.yaml`, `wiki/architecture.yaml`, and `wiki/COMPONENTS.csv`.

Figure refresh:

- `wiki/figures/model-current.d2` updated for Batch9 terminal direct ResEnc path.
- `wiki/figures/model-current.svg` rendered with `d2`.
- `wiki/figures/model-current.png` rendered through ImageMagick fallback after direct D2 PNG export attempted Playwright download and failed.
