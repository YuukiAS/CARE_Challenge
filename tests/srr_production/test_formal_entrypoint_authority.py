from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT = REPO_ROOT / "scripts/srr_production/audit_formal_entrypoints.py"
CONFIG = REPO_ROOT / "configs/srr_production/entrypoints.yaml"


def run_audit(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_default_batch0_config_is_blocked_but_strict_clean() -> None:
    result = run_audit("--strict")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "BLOCKED_PENDING_AUTHORIZED_FOLD0_TRAINING" in result.stdout


def test_b6_known_bad_cannot_be_formal_entrypoint() -> None:
    result = run_audit("--strict", "--known-bad", "legacy_b6")
    assert result.returncode != 0
    assert "forbidden_formal_entrypoint" in result.stdout
    assert "run_B6_joint.py" in result.stdout


def test_b8_known_bad_cannot_be_formal_entrypoint() -> None:
    result = run_audit("--strict", "--known-bad", "legacy_b8")
    assert result.returncode != 0
    assert "forbidden_formal_entrypoint" in result.stdout
    assert "run_B8_registration.py" in result.stdout


def test_b6_job_wrapper_cannot_be_formal_entrypoint(tmp_path: Path) -> None:
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    cfg["formal_training_status"] = "READY"
    cfg["formal_entrypoints"] = [
        {
            "id": "legacy_b6_wrapper",
            "path": "jobs/route_B_round04/run_B6_joint.sh",
            "formal_authority": True,
        }
    ]
    cfg_path = tmp_path / "entrypoints.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    result = run_audit("--strict", "--config", str(cfg_path))
    assert result.returncode != 0
    assert "forbidden_formal_entrypoint" in result.stdout
    assert "run_B6_joint.sh" in result.stdout


def test_random_formal_path_fails(tmp_path: Path) -> None:
    bad_script = tmp_path / "bad_formal.py"
    bad_script.write_text(
        "import torch\n"
        "x = torch.randn(1, 3, 8, 16, 16)\n"
        "dice_proxy = 0.74\n",
        encoding="utf-8",
    )
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    cfg["formal_training_status"] = "READY"
    cfg["formal_entrypoints"] = [
        {
            "id": "tmp_random_formal",
            "path": str(bad_script),
            "formal_authority": True,
        }
    ]
    cfg_path = tmp_path / "entrypoints.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    result = run_audit("--strict", "--config", str(cfg_path))
    assert result.returncode != 0
    assert "formal_random_or_synthetic_science_data" in result.stdout
    assert "formal_hardcoded_or_fixed_metric" in result.stdout
