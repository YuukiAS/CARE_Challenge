"""Route B Round04 MyoPS terminal evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MyoPSTerminalCase:
    case_id: str
    center: str
    scar_positive: bool
    t2_present: bool
    t2_edema_positive: bool

    @property
    def no_t2(self) -> bool:
        return not self.t2_present


def final_delta_positive(value: float) -> bool:
    return value > 0.0
