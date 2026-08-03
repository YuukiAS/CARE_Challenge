import ast
from pathlib import Path

from src.care_myocardium.training.care_ase_runtime import CAREASEFormalRuntime


REPO = Path(__file__).resolve().parents[2]


def test_formal_wrapper_is_thin_and_delegates_to_runtime():
    wrapper = REPO / "scripts/training/care_ase/run_care_ase_r2_chunk.py"
    source = wrapper.read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

    assert "from src.care_myocardium.training.care_ase_runtime import main" in source
    assert "make_batch" not in defined
    assert "deterministic_center" not in defined
    assert "descriptor_bundle_for_step" not in source
    assert "run_formal_optimizer_step" not in source


def test_public_runtime_api_exists_and_owns_formal_step():
    assert CAREASEFormalRuntime.public_api_name.endswith("CAREASEFormalRuntime.run_formal_training_step")
    assert callable(CAREASEFormalRuntime.run_formal_training_step)
