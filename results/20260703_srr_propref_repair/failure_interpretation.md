# Failure Interpretation

experiment_adequacy_decision: FAIL
route_negative_decision: STOP_NOT_SUPPORTED
scientific_resolution_status: SCIENTIFIC_UNDERTRAINED

This executor does not write `STOP_NO_PROPREF_SIGNAL` unless adequacy passes. Missing or short training evidence is classified as undertrained/needs evidence, not as a scientific route stop.

No old SRR-v2 tuning route, fold expansion, validation packaging, upload, label/evaluator change, or split change was launched.
