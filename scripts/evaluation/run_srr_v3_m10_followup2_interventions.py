#!/usr/bin/env python3
"""Follow-up2 D2/D3 real-intervention gate.

This script intentionally fails closed until real graph-node hooks and
final-output manifests are implemented.  It may not emit placeholder rows that
look like successful interventions.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results/20260715_srr_v3_m10_followup2_wave2_evidence_repair"
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
    "no_op_control",
]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_selected() -> dict[str, object]:
    path = OUT_DIR / "selected_checkpoints.json"
    if not path.is_file():
        return {"status": "MISSING"}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps({"task_key": OUT_DIR.name, "interventions": INTERVENTIONS, "placeholder_success_forbidden": True}, indent=2))
        return
    selected = load_selected()
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
                    "hook_identifier": "",
                    "call_count": 0,
                    "activation_variance": "",
                    "baseline_final_label_manifest": "",
                    "intervention_final_label_manifest": "",
                    "changed_voxels": "",
                    "changed_components": "",
                    "dice_delta": "",
                    "hd95_delta": "",
                    "remote_fp_delta": "",
                    "per_case_help_harm": "",
                    "status": "NEEDS_REVISION_REAL_GRAPH_NODE_INTERVENTION_NOT_IMPLEMENTED",
                }
            )
        write_csv(OUT_DIR / target, [row for row in rows if row["phase"] == phase])
        write_csv(OUT_DIR / target.replace("component_interventions", "intervention_output_manifest"), [])
    write_csv(
        OUT_DIR / "component_state_classification.csv",
        [
            {
                "phase": row["phase"],
                "checkpoint_name": row["checkpoint_name"],
                "component": row["intervention"],
                "classification": "NEEDS_REVISION",
                "reason": row["status"],
            }
            for row in rows
        ],
    )
    write_csv(OUT_DIR / "hard_subgroup_help_harm.csv", [{"status": "NEEDS_REVISION", "reason": "intervention_help_harm_requires_real_final_output_hooks"}])
    write_csv(OUT_DIR / "no_t2_safety_report.csv", [{"status": "NEEDS_EVIDENCE", "reason": "fresh no-T2 probability gate not yet proven"}])
    raise SystemExit(3)


if __name__ == "__main__":
    main()
