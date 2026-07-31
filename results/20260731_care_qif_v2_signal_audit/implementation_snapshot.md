# CARE-QIF v2 Implementation Snapshot

- CleanOOFFeatureExtractor: scripts/training/care_qif_v2_signal_audit/build_oof_feature_cache.py
- DeterministicIntensityChannels: scripts/training/care_qif_v2_signal_audit/query_models.py
- CommonScarFeatureStem: scripts/training/care_qif_v2_signal_audit/query_models.py
- DenseParameterMatchedControl: scripts/training/care_qif_v2_signal_audit/query_models.py
- ScarComponentQueryHead: scripts/training/care_qif_v2_signal_audit/query_models.py
- ScarSetMatcher: scripts/training/care_qif_v2_signal_audit/query_losses.py
- ScarComponentQueryLoss: scripts/training/care_qif_v2_signal_audit/query_losses.py
- CrossCenterScarDataset: scripts/training/care_qif_v2_signal_audit/query_dataset.py
- CrossCenterScarEvaluator: scripts/evaluation/care_qif_v2_signal_audit/evaluate_query_pilot.py

The pilot uses clean-OOF features, full-volume physical batch size 1, gradient accumulation 4, and selected checkpoint reload before held-out evaluation.
