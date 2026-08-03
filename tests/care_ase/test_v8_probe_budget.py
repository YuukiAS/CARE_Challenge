import json
from pathlib import Path
import uuid

import pytest

import src.care_myocardium.training.care_ase_runtime as runtime


def test_v8_probe_budget_rejects_twenty_first_optimizer_step(monkeypatch):
    monkeypatch.setattr(runtime, "TASK_KEY", f"pytest_v8_probe_budget_{uuid.uuid4().hex}")

    first = runtime.reserve_v8_probe_budget(fold=1, start_step=0, end_step=20, max_steps=20)
    assert first["total_reserved_optimizer_steps"] == 20

    with pytest.raises(RuntimeError, match="probe budget exceeded before forward"):
        runtime.reserve_v8_probe_budget(fold=4, start_step=0, end_step=1, max_steps=20)


def test_probe_budget_reservation_is_append_only(monkeypatch):
    monkeypatch.setattr(runtime, "TASK_KEY", f"pytest_v8_probe_budget_{uuid.uuid4().hex}")
    first = runtime.reserve_v8_probe_budget(fold=1, start_step=0, end_step=1, max_steps=20)
    second = runtime.reserve_v8_probe_budget(fold=4, start_step=0, end_step=1, max_steps=20)
    ledger = first["append_only_ledger_path"]
    assert ledger == second["append_only_ledger_path"]
    assert second["reserved_step_slots"] == 2
    assert second["reservations"][0]["status"] == "RESERVED_BEFORE_MATERIALIZATION_FORWARD_BACKWARD_STEP"


def test_probe_budget_completion_updates_counter(monkeypatch):
    monkeypatch.setattr(runtime, "TASK_KEY", f"pytest_v8_probe_budget_{uuid.uuid4().hex}")
    receipt = runtime.reserve_v8_probe_budget(fold=1, start_step=0, end_step=2, max_steps=20)
    runtime.record_v8_probe_budget_completion(receipt, status="COMPLETED")
    counter = Path(receipt["counter_path"])
    payload = json.loads(counter.read_text(encoding="utf-8"))
    assert payload["max_optimizer_steps"] == 20
    assert payload["completed_optimizer_steps"] == 2
    assert payload["failed_after_reservation"] == 0
    assert payload["reservations"][0]["completion_status"] == "COMPLETED"
