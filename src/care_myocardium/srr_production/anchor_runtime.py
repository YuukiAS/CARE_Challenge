"""OOF anchor canonicalization runtime for CARE-SRR-Cascade."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import torch


EPSILON = 1e-6
ANCHOR_CHANNELS = 6
REPAIR_ID = "SCR-R1-RC1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonicalize_probabilities(probabilities: torch.Tensor, *, epsilon: float = EPSILON) -> tuple[torch.Tensor, torch.Tensor]:
    if probabilities.ndim != 5:
        raise ValueError("anchor probabilities must be [B, 6, D, H, W]")
    if probabilities.shape[1] != ANCHOR_CHANNELS:
        raise ValueError(f"anchor probabilities must have six channels, got {probabilities.shape[1]}")
    if not torch.isfinite(probabilities).all():
        raise ValueError("anchor probabilities contain nonfinite values")
    if (probabilities < 0).any():
        raise ValueError("anchor probabilities must be nonnegative")
    probs = probabilities.to(dtype=torch.float32).clamp(float(epsilon), 1.0)
    probs = probs / probs.sum(dim=1, keepdim=True).clamp_min(float(epsilon))
    logits = probs.clamp_min(float(epsilon)).log()
    return logits, probs


def anchor_uncertainty(probabilities: torch.Tensor) -> torch.Tensor:
    clipped = probabilities.clamp_min(EPSILON)
    return -(clipped * clipped.log()).sum(dim=1, keepdim=True) / torch.log(torch.tensor(float(probabilities.shape[1])))


def soft_union_probability(probabilities: torch.Tensor) -> torch.Tensor:
    return (probabilities[:, 1:2] + probabilities[:, 4:5] + probabilities[:, 5:6]).clamp(0.0, 1.0)


def distance_to_union_placeholder(probabilities: torch.Tensor) -> torch.Tensor:
    """Fail-closed replacement hook until RC2 computes true physical distance maps."""
    return torch.zeros((probabilities.shape[0], 1, *probabilities.shape[2:]), dtype=probabilities.dtype, device=probabilities.device)


@dataclass(frozen=True)
class AnchorRuntimeRecord:
    case_id: str
    fold: int
    probability_path: str
    probability_sha256: str
    preprocessed_shape: tuple[int, int, int]
    decision: str
    notes: str


def verify_oof_fold(case_id: str, fold: int, allowed_fold: int) -> None:
    if int(fold) != int(allowed_fold):
        raise ValueError(f"OOF_case_uses_wrong_fold: case={case_id} manifest_fold={fold} expected={allowed_fold}")


def load_manifest_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_anchor_cache_tensor(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    torch.save(payload, tmp)
    tmp.replace(path)


def build_synthetic_anchor_cache(
    *,
    case_id: str,
    probabilities: torch.Tensor,
    output_dir: Path,
    fold: int = 0,
    allowed_fold: int = 0,
) -> AnchorRuntimeRecord:
    verify_oof_fold(case_id, fold, allowed_fold)
    logits, probs = canonicalize_probabilities(probabilities)
    payload = {
        "schema_version": 1,
        "repair_id": REPAIR_ID,
        "case_id": str(case_id),
        "canonical_anchor_logits": logits.cpu(),
        "canonical_anchor_probabilities": probs.cpu(),
        "anchor_uncertainty": anchor_uncertainty(probs).cpu(),
        "soft_union_probability": soft_union_probability(probs).cpu(),
        "distance_to_union_mm": distance_to_union_placeholder(probs).cpu(),
        "grid": "resolved_ResEncM_3d_fullres_preprocessed_grid",
        "source_semantics": "five_fold_OOF_only",
    }
    path = output_dir / f"{case_id}__anchor.pt"
    write_anchor_cache_tensor(path, payload)
    return AnchorRuntimeRecord(
        case_id=str(case_id),
        fold=int(fold),
        probability_path=str(path),
        probability_sha256=sha256_file(path),
        preprocessed_shape=tuple(int(v) for v in logits.shape[2:]),
        decision="PASS",
        notes="synthetic preprocessed-grid cache for RC1 API validation; RC2 must build all-220 real cache",
    )


def manifest_cases_complete(rows: Iterable[dict[str, str]], *, expected_cases: int = 220) -> bool:
    return len({row.get("case_id", "") for row in rows}) == int(expected_cases)


def runtime_contract() -> dict[str, Any]:
    return {
        "module": "src.care_myocardium.srr_production.anchor_runtime",
        "canonical_formula": "p=clip(p,epsilon,1);p=p/sum_channels(p);z=log(p)",
        "channels": ANCHOR_CHANNELS,
        "output_grid": "resolved_ResEncM_3d_fullres_preprocessed_grid",
        "source_semantics": "five_fold_OOF_only",
        "hard_label_anchor_forbidden": True,
        "gt_anchor_forbidden": True,
        "rc2_real_all_220_required": True,
    }


def main() -> int:
    print(json.dumps(runtime_contract(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
