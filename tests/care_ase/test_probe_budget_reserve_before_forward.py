import uuid

from src.care_myocardium.training import care_ase_runtime as runtime


def test_probe_budget_reserves_before_forward_status(monkeypatch):
    monkeypatch.setattr(runtime, "TASK_KEY", f"pytest_probe_reserve_{uuid.uuid4().hex}")
    receipt = runtime.reserve_v8_probe_budget(fold=1, start_step=0, end_step=1, max_steps=20)
    assert receipt["latest_reservation"]["status"] == "RESERVED_BEFORE_MATERIALIZATION_FORWARD_BACKWARD_STEP"
