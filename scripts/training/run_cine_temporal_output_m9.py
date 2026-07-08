#!/usr/bin/env python3
"""M9 Cine temporal final-output entrypoint.

This entrypoint is deliberately fail-closed: it can inspect an existing local
prediction directory and write lightweight evidence, but it does not download
weights or claim a trained temporal route when local final outputs are absent.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.temporal_output import inspect_local_cine_prediction_dir


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-pred-dir", required=True)
    parser.add_argument("--out-dir", default="results/20260708_srr_v3_m9_dictionary_fidelity_repair_training")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    status = inspect_local_cine_prediction_dir(Path(args.local_pred_dir))
    write_csv(
        out_dir / "m9_cine_final_output_manifest.csv",
        [status.as_manifest_row()],
        ["status", "case_count", "non_reference_frame_count", "prediction_dir", "message"],
    )
    (out_dir / "m9_cine_final_output_qc.md").write_text(
        "\n".join(
            [
                "# M9 Cine Final-output QC",
                "",
                f"status: `{status.status}`",
                f"case_count: `{status.case_count}`",
                f"non_reference_frame_count: `{status.non_reference_frame_count}`",
                f"prediction_dir: `{status.prediction_dir}`",
                f"message: {status.message}",
                "",
                "No validation package or upload was created.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(status.status)


if __name__ == "__main__":
    main()
