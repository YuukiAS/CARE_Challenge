"""Small MedNeXt factory wrapper for CARE Round17 diagnostics.

The wrapper intentionally reuses the locally audited Round16 MedNeXt clone
instead of vendoring the upstream nnU-Net-v1 training stack into src.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MEDNEXT_REPO = (
    REPO_ROOT
    / "results/diagnostics/care_myocardium/laneA_myops/"
    / "round16_external_mechanism_integration/external_repos/MedNeXt"
)


@dataclass(frozen=True)
class MedNeXtConfig:
    """Minimal CARE-compatible MedNeXt architecture configuration."""

    model_id: str = "S"
    num_input_channels: int = 3
    num_classes: int = 6
    kernel_size: int = 3
    deep_supervision: bool = False


def mednext_repo_path() -> Path:
    """Return the MedNeXt source path selected for local diagnostics."""

    return Path(os.environ.get("CARE_MEDNEXT_REPO", str(DEFAULT_MEDNEXT_REPO))).resolve()


@contextmanager
def _sys_path_prepend(path: Path) -> Iterator[None]:
    path_str = str(path)
    sys.path.insert(0, path_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(path_str)
        except ValueError:
            pass


def create_care_mednext(config: MedNeXtConfig | None = None):
    """Instantiate MedNeXt from the local clone with CARE channel/class counts."""

    cfg = config or MedNeXtConfig()
    repo = mednext_repo_path()
    if not repo.is_dir():
        raise FileNotFoundError(f"MedNeXt repo not found: {repo}")

    with _sys_path_prepend(repo):
        from nnunet_mednext.network_architecture.mednextv1.create_mednext_v1 import (  # noqa: PLC0415
            create_mednext_v1,
        )

        return create_mednext_v1(
            num_input_channels=cfg.num_input_channels,
            num_classes=cfg.num_classes,
            model_id=cfg.model_id,
            kernel_size=cfg.kernel_size,
            deep_supervision=cfg.deep_supervision,
        )
