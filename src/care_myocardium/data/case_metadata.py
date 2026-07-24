"""CARE MyoPS case metadata helpers for modality-aware models."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


MODALITY_ORDER = ("LGE", "T2", "C0")
REAL_MODALITY_GROUPS = ("C0+LGE+T2", "C0+LGE", "LGE-only")


@dataclass(frozen=True)
class MyoPSCaseMetadata:
    case_id: str
    center: str
    modality_group: str
    lge_present: bool
    t2_present: bool
    c0_present: bool

    @property
    def availability(self) -> tuple[float, float, float]:
        return (float(self.lge_present), float(self.t2_present), float(self.c0_present))


def care_root() -> Path:
    return Path(os.environ.get("CARE_ROOT", Path.cwd())).resolve()


def modality_group(lge_present: bool, t2_present: bool, c0_present: bool) -> str:
    if lge_present and t2_present and c0_present:
        return "C0+LGE+T2"
    if lge_present and c0_present and not t2_present:
        return "C0+LGE"
    if lge_present and not t2_present and not c0_present:
        return "LGE-only"
    return "other"


def load_myops_case_metadata(root: Path | None = None) -> dict[str, MyoPSCaseMetadata]:
    """Load case-level center and modality availability from CARE raw data."""

    repo = root or care_root()
    case_json = repo / "data/benchmarks/protocol/cases_MyoPS.json"
    raw_root = repo / "data/CARE_Challenge/MyoPS_train"
    data = json.loads(case_json.read_text(encoding="utf-8"))["cases"]
    out: dict[str, MyoPSCaseMetadata] = {}
    for item in data:
        case_id = str(item["case_id"])
        center = str(item["center"])
        case_dir = raw_root / center / case_id
        lge_present = (case_dir / f"{case_id}_LGE.nii.gz").is_file()
        t2_present = (case_dir / f"{case_id}_T2.nii.gz").is_file()
        c0_present = (case_dir / f"{case_id}_C0.nii.gz").is_file()
        out[case_id] = MyoPSCaseMetadata(
            case_id=case_id,
            center=center,
            modality_group=modality_group(lge_present, t2_present, c0_present),
            lge_present=lge_present,
            t2_present=t2_present,
            c0_present=c0_present,
        )
    return out


def compact_label_mapping() -> dict[int, str]:
    return {
        0: "background",
        1: "myocardium",
        2: "LV_blood",
        3: "RV_blood",
        4: "edema",
        5: "scar",
    }


def compact_to_raw_myops_mapping() -> dict[int, int]:
    return {
        0: 0,
        1: 200,
        2: 500,
        3: 600,
        4: 1220,
        5: 2221,
    }
