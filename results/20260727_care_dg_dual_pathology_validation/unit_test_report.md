# CARE-DG W1 unit test report

`python -m py_compile ...`: PASS.

`python scripts/training/run_care_dg.py --unit-smoke`: PASS.

`python -m pytest tests/care_dg -q`: 7 passed in 3.17s after aligned crop repair.

Real-case forward/backward: PASS on Case3004 complete and Case1002 no-T2 inside allocation 60657290.

300-step implementation overfit: PASS on real Case3004 patch; scar active loss drop 0.9431872009, edema active loss drop 0.9537368986. Formal training credit remains 0.
