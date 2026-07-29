# CARE-ARC W1 Unit Test Report

created_at_utc: 2026-07-29T09:28:47Z
status: PASS

Commands run:

```bash
./envs/env_CARE/bin/python -m pytest -q tests/care_arc/test_care_arc_contract.py
./envs/env_CARE/bin/python scripts/evaluation/validate_care_arc_packet.py --stage implementation --device cpu --output results/20260729_care_arc_clean_fold1/implementation_validator_report.json
```

Observed result: 5 pytest tests passed; implementation validator status PASS.
Trainable parameter count: 24027664.
