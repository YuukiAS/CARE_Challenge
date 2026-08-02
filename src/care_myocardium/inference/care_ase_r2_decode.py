"""CARE-ASE R2 fixed argmax decode and metric-population helpers."""

from __future__ import annotations

from typing import Iterable

import torch


T2_PRESENT_CLASSES = (0, 1, 2, 3, 4, 5)
NO_T2_CLASSES = (0, 1, 2, 3, 5)


def decode_care_ase_r2_logits(logits: torch.Tensor, availability: torch.Tensor) -> torch.Tensor:
    """Fixed CARE-ASE R2 argmax decode.

    T2-present cases use all six classes. No-T2 cases exclude class 4 from the
    competition graph and never remap class 4 to background.
    """

    if logits.ndim < 3 or logits.shape[1] != 6:
        raise ValueError("CARE-ASE R2 logits must have six class channels [0,1,2,3,4,5]")
    availability = availability.to(device=logits.device)
    if availability.ndim != 2 or availability.shape[1] != 3:
        raise ValueError("availability must be [B,3] ordered [LGE,T2,C0]")
    decoded = torch.empty((logits.shape[0], *logits.shape[2:]), dtype=torch.long, device=logits.device)
    t2_present = availability[:, 1] > 0.5
    if bool(t2_present.any()):
        decoded[t2_present] = logits[t2_present].argmax(dim=1)
    if bool((~t2_present).any()):
        class_index = torch.tensor(NO_T2_CLASSES, dtype=torch.long, device=logits.device)
        local = logits[~t2_present].index_select(1, class_index).argmax(dim=1)
        decoded[~t2_present] = class_index[local]
    return decoded


def scar_metric_population(case_ids: Iterable[str]) -> list[str]:
    return sorted(str(case_id) for case_id in case_ids)


def pure_edema_metric_population(case_availability: dict[str, tuple[float, float, float]]) -> list[str]:
    return sorted(str(case_id) for case_id, availability in case_availability.items() if float(availability[1]) > 0.5)
