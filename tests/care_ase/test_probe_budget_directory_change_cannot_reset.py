import uuid

import pytest

from src.care_myocardium.training import care_ase_runtime as runtime


def test_probe_budget_directory_change_cannot_reset(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "TASK_KEY", f"pytest_probe_dir_{uuid.uuid4().hex}")
    runtime.reserve_v8_probe_budget(fold=1, start_step=0, end_step=20, max_steps=20)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="probe budget exceeded before forward"):
        runtime.reserve_v8_probe_budget(fold=4, start_step=0, end_step=1, max_steps=20)
