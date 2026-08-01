from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import torch


def load_nifti(path: str | Path) -> tuple[np.ndarray, np.ndarray, tuple[float, ...], nib.Nifti1Header]:
    image = nib.load(str(path))
    data = np.asarray(image.dataobj)
    affine = image.affine
    spacing = image.header.get_zooms()[: data.ndim]
    return data, affine, spacing, image.header


def save_nifti(
    array: np.ndarray, path: str | Path, affine: np.ndarray, header: nib.Nifti1Header | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(array, affine=affine, header=header)
    nib.save(image, str(path))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl(records: list[dict[str, Any]], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def torch_save(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(obj, path)


def torch_load(path: str | Path, map_location: str | torch.device = "cpu") -> Any:
    return torch.load(path, map_location=map_location, weights_only=False)
