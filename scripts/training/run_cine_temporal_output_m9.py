#!/usr/bin/env python3
"""M9 Cine temporal final-output entrypoint.

This entrypoint is deliberately fail-closed: it can inspect an existing local
prediction directory and write lightweight evidence, but it does not download
weights or claim a trained temporal route when local final outputs are absent.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp/matplotlib"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.temporal_output import inspect_local_cine_prediction_dir, run_local_temporal_output


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
    parser.add_argument("--run-local-temporal-output", action="store_true")
    parser.add_argument(
        "--safe-cases",
        default="results/20260703_cine_motion/safe_cases_used.csv",
    )
    parser.add_argument(
        "--cinema-pred-root",
        default="results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train",
    )
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--pairs-per-case", type=int, default=1)
    parser.add_argument("--antspy-iterations", type=int, default=25)
    parser.add_argument("--demons-iterations", type=int, default=40)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    if args.run_local_temporal_output:
        summary = run_local_temporal_output(
            repo_root=REPO_ROOT,
            out_dir=out_dir,
            pred_root=REPO_ROOT / args.cinema_pred_root,
            safe_cases=REPO_ROOT / args.safe_cases,
            max_cases=args.max_cases,
            pairs_per_case=args.pairs_per_case,
            antspy_iterations=args.antspy_iterations,
            demons_iterations=args.demons_iterations,
        )
        status = str(summary["status"])
        (out_dir / "m9_cine_final_output_qc.md").write_text(
            "\n".join(
                [
                    "# M9 Cine Final-output QC",
                    "",
                    f"status: `{status}`",
                    f"case_count: `{summary['case_count']}`",
                    f"non_reference_frame_count: `{summary['non_reference_frame_count']}`",
                    f"prediction_dir: `{summary['prediction_dir']}`",
                    f"registration_method: `{summary['registration_method']}`",
                    "",
                    "This is a local safe-subset temporal final-output run using existing local CineMA frame-wise anatomy predictions.",
                    "It writes runtime NIfTI predictions under an ignored directory and commits only lightweight evidence.",
                    "No validation package, upload, hosted metric, route promotion, fold expansion, scientific stop, or M10 was created.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (out_dir / "m9_cine_architecture_contract.md").write_text(
            "\n".join(
                [
                    "# M9 Cine Architecture Contract",
                    "",
                    f"status: `{status}`",
                    "",
                    "mode: `mode_A_registration_temporal_dictionary`",
                    "",
                    "Pipeline:",
                    "",
                    "```text",
                    "Cine input sequence",
                    "-> frame 0 reference anchor",
                    "-> safe-case descriptor-selected non-reference frame",
                    "-> existing local CineMA frame-wise anatomy predictions",
                    "-> ANTsPy SyNOnly registration when available, SimpleITK Demons fallback otherwise",
                    "-> temporal representation slots: reference_frame, registered_nonreference_anatomy, quality_weighted_union",
                    "-> deterministic temporal compact-label proxy output",
                    "-> local same-subset metrics vs frame0/reference control",
                    "```",
                    "",
                    "Caveat: this is a local final-output proxy run, not a hosted myocardium_cinemyops metric claim.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (out_dir / "m9_cine_weight_provenance.md").write_text(
            "\n".join(
                [
                    "# M9 Cine Weight Provenance",
                    "",
                    "status: `LOCAL_EXISTING_CINEMA_FRAMEWISE_ARTIFACTS_USED`",
                    "",
                    f"framewise_prediction_root: `{REPO_ROOT / args.cinema_pred_root}`",
                    "",
                    "No weights were downloaded by M9. The run reuses existing local CineMA adapter predictions as anatomy evidence and records them as context/proxy, not as hosted final metric proof.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (out_dir / "m9_cine_reference_frame_contract.md").write_text(
            "\n".join(
                [
                    "# M9 Cine Reference-frame Contract",
                    "",
                    "status: `REFERENCE_FRAME_0_WITH_DESCRIPTOR_SELECTED_NONREFERENCE`",
                    "",
                    "The local M9 Cine run uses frame 0 as the reference anchor and one descriptor-selected non-reference frame per safe case when available. Non-reference frames come from `results/20260703_cine_motion/safe_cases_used.csv`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        next_action = "REVIEW_LOCAL_CINE_PROXY_OUTPUTS_WITH_MYOps_M9_RESULTS"
        (out_dir / "m9_cine_next_required_action.md").write_text(
            "\n".join(
                [
                    "# M9 Cine Next Required Action",
                    "",
                    f"status: `{status}`",
                    "",
                    f"next_required_action: `{next_action}`",
                    "",
                    "Do not upload or claim hosted myocardium_cinemyops readiness from this local proxy evidence alone.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print(status)
        return

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
