#!/usr/bin/env python3
"""Record F1 intervention readiness for D2/D3 selected checkpoints."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results/20260714_srr_v3_m10_followup_wave2_reconciliation"
INTERVENTIONS = [
    "static_mixture",
    "dictionary_uniform_valid",
    "top_pathology_slots_zeroed",
    "spatial_router_to_global",
    "PSIP_stateless",
    "prototype_memory_off",
    "anatomy_prior_flat",
    "proposal_only",
    "scar_refiner_off",
    "edema_refiner_off",
    "both_refiners_off",
    "uncertainty_flat",
    "nnunet_context_off",
    "alignment_off",
    "swapped_positive_negative_known_bad",
]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps({"task_key": "20260714_srr_v3_m10_followup_wave2_reconciliation", "interventions": INTERVENTIONS}, indent=2))
        return
    selected_path = OUT_DIR / "selected_checkpoints.json"
    selected = json.loads(selected_path.read_text(encoding="utf-8")) if selected_path.is_file() else {"phases": {}}
    rows: list[dict[str, object]] = []
    for phase, target in (("d2_hierarchical_psip", "d2_component_interventions.csv"), ("d3_full_propref", "d3_component_interventions.csv")):
        phase_selected = selected.get("phases", {}).get(phase, {}) if isinstance(selected.get("phases"), dict) else {}
        checkpoint = phase_selected.get("checkpoint_name", "")
        for intervention in INTERVENTIONS:
            rows.append(
                {
                    "phase": phase,
                    "checkpoint_name": checkpoint,
                    "intervention": intervention,
                    "call_count": "NEEDS_EVIDENCE",
                    "gradient_status": "NEEDS_EVIDENCE",
                    "activation_variance": "NEEDS_EVIDENCE",
                    "proposal_logit_delta": "NEEDS_EVIDENCE",
                    "refiner_logit_delta": "NEEDS_EVIDENCE",
                    "final_logit_delta": "NEEDS_EVIDENCE",
                    "changed_voxels": "NEEDS_EVIDENCE",
                    "changed_components": "NEEDS_EVIDENCE",
                    "dice_delta": "NEEDS_EVIDENCE",
                    "hd95_delta": "NEEDS_EVIDENCE",
                    "remote_fp_delta": "NEEDS_EVIDENCE",
                    "per_case_help_harm": "NEEDS_EVIDENCE",
                    "status": "NEEDS_EVIDENCE_SELECTED_CHECKPOINT_INTERVENTION_NOT_YET_RUN",
                }
            )
        write_csv(OUT_DIR / target, [row for row in rows if row["phase"] == phase])
    classification = [
        {
            "phase": row["phase"],
            "checkpoint_name": row["checkpoint_name"],
            "component": row["intervention"],
            "classification": "NEEDS_EVIDENCE",
            "reason": row["status"],
        }
        for row in rows
    ]
    write_csv(OUT_DIR / "component_state_classification.csv", classification)


if __name__ == "__main__":
    main()
