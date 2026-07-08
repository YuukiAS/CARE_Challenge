"""Small first-party temporal output helpers for M9 Cine evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CineTemporalRunStatus:
    status: str
    case_count: int
    non_reference_frame_count: int
    prediction_dir: str
    message: str

    def as_manifest_row(self) -> dict[str, object]:
        return {
            "status": self.status,
            "case_count": self.case_count,
            "non_reference_frame_count": self.non_reference_frame_count,
            "prediction_dir": self.prediction_dir,
            "message": self.message,
        }


def inspect_local_cine_prediction_dir(path: Path) -> CineTemporalRunStatus:
    predictions = sorted(path.glob("**/*_pred.nii.gz")) if path.is_dir() else []
    return CineTemporalRunStatus(
        status="FOUND_LOCAL_FINAL_OUTPUTS" if predictions else "M9_NEEDS_EVIDENCE_CINE_LOCAL_BACKBONE_MISSING",
        case_count=len(predictions),
        non_reference_frame_count=0,
        prediction_dir=str(path),
        message="local compact-label final outputs found" if predictions else "no local Cine final-output predictions found",
    )
