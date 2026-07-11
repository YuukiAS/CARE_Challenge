# Validator Report

Final successful checks:

```text
python scripts/validation/validate_handoff_policy.py --policy --warnings-as-errors
python scripts/validation/validate_handoff_policy.py --candidate tests/fixtures/agent_flow/valid_high_risk_M27.md
python scripts/validation/validate_handoff_policy.py --packet results/20260711_agent_flow_generic_protocol_repair
python scripts/ops/validate_executor_plan.py tests/fixtures/agent_flow/valid_high_risk_M27_executor_plan.yaml
python scripts/architecture/validate_care_architecture_wiki.py --strict --history
python scripts/architecture/generate_care_architecture_wiki.py --check-all
python scripts/architecture/create_care_history_snapshot.py --milestone M27 --dry-run
python -m unittest src.care_myocardium.tests.test_handoff_policy_validator
python -m py_compile scripts/validation/validate_handoff_policy.py scripts/validation/hash_milestone_contract.py scripts/agent_flow/milestone_id.py scripts/ops/validate_executor_plan.py scripts/ops/prepare_care_executor_wave.py scripts/ops/merge_care_executor_wave.py scripts/architecture/create_care_history_snapshot.py scripts/architecture/generate_care_architecture_wiki.py scripts/architecture/validate_care_architecture_wiki.py scripts/architecture/reconcile_review_status.py
git diff --check
```

All commands exited `0`. The active hardcode scan for forbidden concrete
milestone-number control-flow patterns returned no matches.
