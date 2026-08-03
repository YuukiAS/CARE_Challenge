import multiprocessing as mp
import uuid

from src.care_myocardium.training import care_ase_runtime as runtime


def _reserve(task_key: str):
    runtime.TASK_KEY = task_key
    try:
        runtime.reserve_v8_probe_budget(fold=1, start_step=0, end_step=1, max_steps=20)
        return "reserved"
    except RuntimeError:
        return "rejected"


def test_probe_budget_parallel_reservation_max20():
    task_key = f"pytest_probe_parallel_{uuid.uuid4().hex}"
    with mp.Pool(processes=21) as pool:
        results = pool.map(_reserve, [task_key] * 21)
    assert results.count("reserved") == 20
    assert results.count("rejected") == 1
