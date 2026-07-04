"""MyoPS anchor availability and compact-label decode guardrails."""

from __future__ import annotations

from typing import Literal

import torch


CANONICAL_AVAILABILITY_ORDER = ("LGE", "T2", "C0")
LEGACY_PRESENCE_ORDER = ("C0", "LGE", "T2")
NO_T2_EDEMA_POLICIES = ("block_edema", "baseline_passthrough", "diagnostic_only")

BACKGROUND_CLASS = 0
EDEMA_CLASS = 4
SCAR_CLASS = 5
BLOCKED_LOGIT_VALUE = -1.0e9

NoT2EdemaPolicy = Literal["block_edema", "baseline_passthrough", "diagnostic_only"]

MYOPS_COMPACT_TO_RAW = {
    0: 0,
    1: 200,
    2: 500,
    3: 600,
    4: 1220,
    5: 2221,
}


def _canonical_order(order: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(str(item) for item in order)


def assert_canonical_availability_order(order: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Return the canonical order or raise on any non-canonical order."""

    normalized = _canonical_order(order)
    if normalized != CANONICAL_AVAILABILITY_ORDER:
        raise ValueError(
            "MyoPS availability must use canonical order "
            f"{CANONICAL_AVAILABILITY_ORDER}; got {normalized}"
        )
    return normalized


def normalize_availability_order(
    availability: torch.Tensor,
    order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    *,
    allow_legacy_adapter: bool = False,
) -> torch.Tensor:
    """Return availability in canonical ``LGE,T2,C0`` order.

    The legacy ``C0,LGE,T2`` order is adapted only when
    ``allow_legacy_adapter=True``. All other non-canonical orders raise.
    """

    normalized = _canonical_order(order)
    if availability.shape[-1] != 3:
        raise ValueError(f"expected availability last dimension of 3, got {tuple(availability.shape)}")
    if normalized == CANONICAL_AVAILABILITY_ORDER:
        return availability
    if normalized == LEGACY_PRESENCE_ORDER and allow_legacy_adapter:
        return availability[..., [1, 2, 0]]
    if normalized == LEGACY_PRESENCE_ORDER:
        raise ValueError(
            "Legacy MyoPS presence order C0,LGE,T2 requires allow_legacy_adapter=True; "
            "implicit adaptation is forbidden."
        )
    raise ValueError(
        "Unsupported MyoPS availability order. Expected canonical "
        f"{CANONICAL_AVAILABILITY_ORDER}; got {normalized}"
    )


def canonical_t2_present(
    availability: torch.Tensor,
    order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    *,
    allow_legacy_adapter: bool = False,
) -> torch.Tensor:
    """Return a boolean T2-present vector from availability metadata."""

    canonical = normalize_availability_order(
        availability,
        order,
        allow_legacy_adapter=allow_legacy_adapter,
    )
    if canonical.ndim == 1:
        canonical = canonical.unsqueeze(0)
    return canonical[..., 1].to(dtype=torch.bool)


def _validate_policy(policy: str) -> NoT2EdemaPolicy:
    if policy not in NO_T2_EDEMA_POLICIES:
        raise ValueError(f"unknown no-T2 edema policy {policy!r}; expected one of {NO_T2_EDEMA_POLICIES}")
    return policy  # type: ignore[return-value]


def _as_batch_mask(mask: torch.Tensor, batch: int, target_ndim: int, device: torch.device) -> torch.Tensor:
    if mask.ndim != 1:
        mask = mask.reshape(-1)
    if mask.numel() == 1 and batch != 1:
        mask = mask.expand(batch)
    if mask.numel() != batch:
        raise ValueError(f"availability batch {mask.numel()} does not match tensor batch {batch}")
    mask = mask.to(device=device, dtype=torch.bool)
    while mask.ndim < target_ndim:
        mask = mask[..., None]
    return mask


def apply_no_t2_edema_policy_to_logits(
    logits: torch.Tensor,
    availability: torch.Tensor,
    *,
    policy: NoT2EdemaPolicy,
    availability_order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    allow_legacy_availability_order: bool = False,
    baseline_logits: torch.Tensor | None = None,
    edema_class: int = EDEMA_CLASS,
    blocked_logit_value: float = BLOCKED_LOGIT_VALUE,
) -> torch.Tensor:
    """Apply the no-T2 edema policy to batched compact-class logits.

    ``logits`` must have shape ``(B, C, ...)`` and compact class 4 is edema.
    Under ``block_edema``, edema logits are set to a very low value for no-T2
    samples before argmax decode.
    """

    policy = _validate_policy(policy)
    if logits.ndim < 3:
        raise ValueError(f"expected logits shape (B,C,...), got {tuple(logits.shape)}")
    if logits.shape[1] <= edema_class:
        raise ValueError(f"expected at least {edema_class + 1} compact classes, got {logits.shape[1]}")

    t2_present = canonical_t2_present(
        availability.to(device=logits.device),
        availability_order,
        allow_legacy_adapter=allow_legacy_availability_order,
    )
    no_t2 = ~t2_present
    if not bool(no_t2.any()):
        return logits

    guarded = logits.clone()
    no_t2_mask = _as_batch_mask(no_t2, logits.shape[0], guarded[:, edema_class].ndim, logits.device)

    if policy == "diagnostic_only":
        return guarded
    if policy == "baseline_passthrough":
        if baseline_logits is None:
            raise ValueError("baseline_passthrough requires baseline_logits for logit-level gating")
        if baseline_logits.shape != logits.shape:
            raise ValueError(f"baseline_logits shape {tuple(baseline_logits.shape)} does not match logits {tuple(logits.shape)}")
        baseline_edema = baseline_logits.to(device=logits.device, dtype=logits.dtype)[:, edema_class]
        guarded[:, edema_class] = torch.where(no_t2_mask, baseline_edema, guarded[:, edema_class])
        return guarded

    blocked = torch.full_like(guarded[:, edema_class], float(blocked_logit_value))
    guarded[:, edema_class] = torch.where(no_t2_mask, blocked, guarded[:, edema_class])
    return guarded


def decode_compact_logits(
    logits: torch.Tensor,
    availability: torch.Tensor,
    *,
    policy: NoT2EdemaPolicy = "block_edema",
    availability_order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    allow_legacy_availability_order: bool = False,
    baseline_logits: torch.Tensor | None = None,
    baseline_compact: torch.Tensor | None = None,
    edema_class: int = EDEMA_CLASS,
) -> torch.Tensor:
    """Decode compact MyoPS labels while enforcing the no-T2 edema policy."""

    guarded_logits = apply_no_t2_edema_policy_to_logits(
        logits,
        availability,
        policy=policy,
        availability_order=availability_order,
        allow_legacy_availability_order=allow_legacy_availability_order,
        baseline_logits=baseline_logits,
        edema_class=edema_class,
    )
    decoded = torch.argmax(guarded_logits, dim=1).to(dtype=torch.long)
    if policy == "baseline_passthrough" and baseline_compact is not None:
        if baseline_compact.shape != decoded.shape:
            raise ValueError(f"baseline_compact shape {tuple(baseline_compact.shape)} does not match decoded {tuple(decoded.shape)}")
        t2_present = canonical_t2_present(
            availability.to(device=logits.device),
            availability_order,
            allow_legacy_adapter=allow_legacy_availability_order,
        )
        no_t2_mask = _as_batch_mask(~t2_present, decoded.shape[0], decoded.ndim, decoded.device)
        decoded = torch.where(no_t2_mask, baseline_compact.to(device=decoded.device, dtype=decoded.dtype), decoded)
    return decoded


def apply_no_t2_edema_policy_to_decoded(
    decoded: torch.Tensor,
    availability: torch.Tensor,
    *,
    policy: NoT2EdemaPolicy,
    availability_order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    allow_legacy_availability_order: bool = False,
    baseline_compact: torch.Tensor | None = None,
    edema_class: int = EDEMA_CLASS,
) -> torch.Tensor:
    """Apply the no-T2 edema policy to already decoded compact labels."""

    policy = _validate_policy(policy)
    if decoded.ndim < 2:
        raise ValueError(f"expected decoded shape (B,...), got {tuple(decoded.shape)}")
    t2_present = canonical_t2_present(
        availability.to(device=decoded.device),
        availability_order,
        allow_legacy_adapter=allow_legacy_availability_order,
    )
    no_t2 = ~t2_present
    if not bool(no_t2.any()) or policy == "diagnostic_only":
        return decoded
    no_t2_mask = _as_batch_mask(no_t2, decoded.shape[0], decoded.ndim, decoded.device)
    guarded = decoded.clone()
    if policy == "baseline_passthrough":
        if baseline_compact is None:
            raise ValueError("baseline_passthrough requires baseline_compact for decoded-label gating")
        if baseline_compact.shape != decoded.shape:
            raise ValueError(f"baseline_compact shape {tuple(baseline_compact.shape)} does not match decoded {tuple(decoded.shape)}")
        return torch.where(no_t2_mask, baseline_compact.to(device=decoded.device, dtype=decoded.dtype), guarded)
    guarded = torch.where(no_t2_mask & (guarded == edema_class), torch.zeros_like(guarded), guarded)
    return guarded


def count_no_t2_edema_voxels(
    decoded: torch.Tensor,
    availability: torch.Tensor,
    *,
    availability_order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    allow_legacy_availability_order: bool = False,
    edema_class: int = EDEMA_CLASS,
) -> int:
    """Count compact edema voxels in samples whose T2 channel is unavailable."""

    if decoded.ndim < 2:
        raise ValueError(f"expected decoded shape (B,...), got {tuple(decoded.shape)}")
    t2_present = canonical_t2_present(
        availability.to(device=decoded.device),
        availability_order,
        allow_legacy_adapter=allow_legacy_availability_order,
    )
    no_t2_mask = _as_batch_mask(~t2_present, decoded.shape[0], decoded.ndim, decoded.device)
    return int(((decoded == int(edema_class)) & no_t2_mask).sum().detach().cpu().item())


def compact_to_raw_myops(decoded: torch.Tensor, *, unknown_value: int | None = None) -> torch.Tensor:
    """Map Dataset501 compact labels to CARE MyoPS raw submission labels."""

    raw = torch.empty_like(decoded, dtype=torch.long)
    assigned = torch.zeros_like(decoded, dtype=torch.bool)
    for compact, raw_label in MYOPS_COMPACT_TO_RAW.items():
        mask = decoded == int(compact)
        raw = torch.where(mask, torch.full_like(raw, int(raw_label)), raw)
        assigned = assigned | mask
    if bool((~assigned).any().item()):
        if unknown_value is None:
            values = torch.unique(decoded[~assigned]).detach().cpu().tolist()
            raise ValueError(f"decoded compact labels contain unknown values: {values}")
        raw = torch.where(assigned, raw, torch.full_like(raw, int(unknown_value)))
    return raw


def decode_myops_logits_for_export_policy(
    logits: torch.Tensor,
    availability: torch.Tensor,
    *,
    policy: NoT2EdemaPolicy = "block_edema",
    availability_order: tuple[str, ...] | list[str] = CANONICAL_AVAILABILITY_ORDER,
    allow_legacy_availability_order: bool = False,
    baseline_logits: torch.Tensor | None = None,
    baseline_compact: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, int | str]]:
    """Decode compact logits, enforce no-T2 policy, and map to raw labels.

    This is an export-policy helper only: it does not write NIfTI files or
    create a validation package. Callers still need geometry-preserving export.
    """

    pre_policy = torch.argmax(logits, dim=1).to(dtype=torch.long)
    decoded = decode_compact_logits(
        logits,
        availability,
        policy=policy,
        availability_order=availability_order,
        allow_legacy_availability_order=allow_legacy_availability_order,
        baseline_logits=baseline_logits,
        baseline_compact=baseline_compact,
    )
    decoded = apply_no_t2_edema_policy_to_decoded(
        decoded,
        availability,
        policy=policy,
        availability_order=availability_order,
        allow_legacy_availability_order=allow_legacy_availability_order,
        baseline_compact=baseline_compact,
    )
    raw = compact_to_raw_myops(decoded)
    summary: dict[str, int | str] = {
        "policy": policy,
        "no_t2_edema_voxels_before": count_no_t2_edema_voxels(
            pre_policy,
            availability,
            availability_order=availability_order,
            allow_legacy_availability_order=allow_legacy_availability_order,
        ),
        "no_t2_edema_voxels_after": count_no_t2_edema_voxels(
            decoded,
            availability,
            availability_order=availability_order,
            allow_legacy_availability_order=allow_legacy_availability_order,
        ),
        "compact_edema_label": int(EDEMA_CLASS),
        "raw_edema_label": int(MYOPS_COMPACT_TO_RAW[EDEMA_CLASS]),
        "raw_scar_label": int(MYOPS_COMPACT_TO_RAW[SCAR_CLASS]),
    }
    return decoded, raw, summary
