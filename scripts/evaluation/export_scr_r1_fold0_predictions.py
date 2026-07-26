#!/usr/bin/env python3
"""Export SCR-R1 selected control predictions for fold0 canonical comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_care_srr_cascade import (  # noqa: E402
    RESULT_ROOT as SCR_RESULT_ROOT,
    candidate_logits,
    full_case_batch,
    load_models,
    source_path_map,
)
from scripts.inference.run_care_mm_batch10_fair_inference import (  # noqa: E402
    PREPROCESSED_DIR,
    export_logits,
    sha256_file,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.srr_production.case_prototypes import select_crossfit_prototype_bank  # noqa: E402

PATHOLOGY_TO_DIR = {"scar": "scar", "edema": "pure_edema"}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fold0_val_cases(split_path: Path) -> list[str]:
    payload = json.loads(split_path.read_text(encoding="utf-8"))
    folds = payload["folds"]
    return [str(case_id) for case_id in folds[0]["val"]]


def selected_candidate(pathology: str) -> tuple[str, dict[str, Any]]:
    decision_path = SCR_RESULT_ROOT / f"w4_final_decision_{pathology}_v2.json"
    payload = json.loads(decision_path.read_text(encoding="utf-8"))
    candidate = str(payload.get("selected_candidate") or "")
    if not candidate:
        raise RuntimeError(f"SCR-R1 {pathology} selected_candidate is missing in {decision_path}")
    return candidate, payload


def load_properties(case_id: str) -> dict[str, Any]:
    with (PREPROCESSED_DIR / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    if not isinstance(props, dict):
        raise TypeError(f"nnU-Net properties for {case_id} must be a dict")
    return props


def expected_argmax_hashes() -> dict[tuple[str, str, str], str]:
    out: dict[tuple[str, str, str], str] = {}
    for row in read_csv_rows(SCR_RESULT_ROOT / "full44_final_candidate_metrics_v2.csv"):
        case_id = str(row.get("case_id") or "")
        pathology = str(row.get("pathology") or "")
        candidate = str(row.get("candidate") or "")
        sha = str(row.get("prediction_argmax_sha256") or "")
        if case_id and pathology and candidate and sha:
            out[(case_id, pathology, candidate)] = sha
    return out


def export_pathology(
    *,
    pathology: str,
    cases: list[str],
    output_root: Path,
    device: torch.device,
    force: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate, decision = selected_candidate(pathology)
    metadata = load_myops_case_metadata(REPO_ROOT)
    paths = source_path_map()
    records = [torch.load(path, map_location="cpu", weights_only=False) for path in sorted((SCR_RESULT_ROOT / "runtime/prototype_cache_v2").glob("*__prototypes.pt"))]
    split_rows = read_csv_rows(REPO_ROOT / "results/20260724_care_myops_batch10_deadline_rescue/rescue_split_manifest.csv")
    fold0_val_set = {row["case_id"] for row in split_rows}
    all_anchor_cases = {path.name.split("__", 1)[0] for path in (SCR_RESULT_ROOT / "runtime/anchor_cache_v2").glob("*__anchor.pt")}
    train_cases = all_anchor_cases - fold0_val_set
    bank_records = [record for record in records if record.case_id in train_cases]
    if len(bank_records) != 176:
        raise RuntimeError(f"SCR-R1 prototype bank must have 176 fold0 train records, got {len(bank_records)}")
    models, checkpoint_rows = load_models(pathology, device)
    expected_hash = expected_argmax_hashes()
    out_dir = output_root / PATHOLOGY_TO_DIR[pathology]
    rows: list[dict[str, Any]] = []
    out_dir.mkdir(parents=True, exist_ok=True)

    for index, case_id in enumerate(cases):
        out_truncated = out_dir / case_id
        out_path = out_dir / f"{case_id}.nii.gz"
        batch, _gt = full_case_batch(
            case_id,
            pathology=pathology,
            metadata=metadata,
            paths=paths,
            records=records,
            bank_records=bank_records,
            device=device,
        )
        with torch.inference_mode():
            logits_t = candidate_logits(pathology=pathology, candidate=candidate, batch=batch, models=models)
        logits = logits_t[0].detach().cpu().numpy().astype(np.float32, copy=False)
        argmax = logits.argmax(axis=0).astype(np.int16, copy=False)
        argmax_sha = hashlib.sha256(argmax.tobytes()).hexdigest()
        expected = expected_hash.get((case_id, pathology, candidate), "")
        hash_match = bool(expected and expected == argmax_sha)
        hash_status = "MATCH" if hash_match else ("MISMATCH_RECOMPUTED_CURRENT_CODE" if expected else "NO_PREEXISTING_HASH")
        if force or not out_path.is_file():
            export_logits(logits, load_properties(case_id), out_truncated, save_probabilities=False, save_preprocessed_logits=False)
        rows.append(
            {
                "case_id": case_id,
                "case_index": index,
                "pathology": pathology,
                "candidate": candidate,
                "decision": decision.get("decision"),
                "audit_pass": decision.get("audit_pass"),
                "prediction_path": str(out_path.relative_to(REPO_ROOT)),
                "prediction_sha256": sha256_file(out_path) if out_path.is_file() else "",
                "preprocessed_argmax_sha256": argmax_sha,
                "preexisting_metric_argmax_sha256": expected,
                "preexisting_metric_hash_match": hash_match,
                "preexisting_metric_hash_status": hash_status,
                "label_space": "compact",
                "export_method": "nnunetv2.export_prediction_from_logits",
            }
        )
    return rows, {
        "pathology": pathology,
        "selected_candidate": candidate,
        "decision": decision,
        "checkpoint_rows": checkpoint_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-path", type=Path, default=REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction/scr_r1_predictions")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cases = fold0_val_cases(args.split_path)
    device = torch.device(args.device if args.device != "cuda" or torch.cuda.is_available() else "cpu")
    all_rows: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for pathology in ("scar", "edema"):
        rows, decision = export_pathology(pathology=pathology, cases=cases, output_root=args.output_root, device=device, force=args.force)
        all_rows.extend(rows)
        decisions.append(decision)
    write_csv(args.output_root / "prediction_manifest.csv", all_rows)
    receipt = {
        "status": "PASS",
        "case_count": len(cases),
        "pathology_count": 2,
        "prediction_rows": len(all_rows),
        "output_root": str(args.output_root.relative_to(REPO_ROOT)),
        "device": str(device),
        "decisions": decisions,
        "notes": "Exports SCR-R1 selected candidates for fold0 canonical comparison only; no training, validation upload, Docker, or push.",
    }
    write_json(args.output_root / "export_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
