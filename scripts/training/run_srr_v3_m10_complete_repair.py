#!/usr/bin/env python3
"""Run M10 SRR-v3 MyoPS training phases through the owned M10 entrypoint.

This wrapper exists because the legacy fold0 training CLI does not accept the
new M10 variant names, while its internal training function can run them.  The
wrapper keeps M10 phase budgets, output roots, and ablation flags explicit
without editing the legacy script.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training import run_srr_propref_myops_fold0 as legacy  # noqa: E402


_LEGACY_PROPREF_LOSS = legacy.propref_loss


def _m10_propref_loss_with_compat_metrics(*args, **kwargs):
    total, metrics = _LEGACY_PROPREF_LOSS(*args, **kwargs)
    zero = total.detach() * 0.0
    metrics.setdefault("correction_opportunity_loss", zero)
    return total, metrics


legacy.propref_loss = _m10_propref_loss_with_compat_metrics


@dataclass(frozen=True)
class PhaseSpec:
    phase: str
    design: str
    variant: str
    result_dir: str
    min_steps: int
    min_train_loop_seconds: int
    min_validation_events: int
    min_full_case_events: int
    min_eval_cases: int
    run_label: str
    disable_nnunet_anchor: bool = False
    hardneg_sample_prob: float | None = None
    alignment_control: bool = False
    description: str = ""


PHASES: dict[str, PhaseSpec] = {
    "d0_control": PhaseSpec(
        phase="d0_control",
        design="D0_STATIC_MATCHED_PROPREF",
        variant="m10_d0_static_matched_propref",
        result_dir="results/20260711_srr_v3_m10_myops_d0_control",
        min_steps=20000,
        min_train_loop_seconds=7200,
        min_validation_events=12,
        min_full_case_events=4,
        min_eval_cases=44,
        run_label="m10_d0_static_matched_formal",
        description="Parameter-matched static PropRef control.",
    ),
    "d1_spatial_br2": PhaseSpec(
        phase="d1_spatial_br2",
        design="D1_SPATIAL_BR2_PROPREF",
        variant="m10_d1_spatial_br2_propref",
        result_dir="results/20260711_srr_v3_m10_myops_d1_spatial_br2",
        min_steps=25000,
        min_train_loop_seconds=9000,
        min_validation_events=15,
        min_full_case_events=5,
        min_eval_cases=44,
        run_label="m10_d1_spatial_br2_formal",
        description="One-pass spatial BR2 formal run.",
    ),
    "d2_hierarchical_psip": PhaseSpec(
        phase="d2_hierarchical_psip",
        design="D2_HIERARCHICAL_BR2_PSIP_PROPREF",
        variant="m10_d2_hierarchical_psip_propref",
        result_dir="results/20260711_srr_v3_m10_myops_d2_hierarchical_psip",
        min_steps=25000,
        min_train_loop_seconds=9000,
        min_validation_events=15,
        min_full_case_events=5,
        min_eval_cases=44,
        run_label="m10_d2_hierarchical_psip_formal",
        description="Two-pass spatial BR2 plus independent Pattern-SIP.",
    ),
    "d3_full_propref": PhaseSpec(
        phase="d3_full_propref",
        design="D3_HIERARCHICAL_BR2_MEMORY_PROPREF",
        variant="m10_d3_hierarchical_memory_propref",
        result_dir="results/20260711_srr_v3_m10_myops_d3_full_propref",
        min_steps=45000,
        min_train_loop_seconds=14400,
        min_validation_events=22,
        min_full_case_events=8,
        min_eval_cases=44,
        run_label="m10_d3_full_memory_propref_formal",
        hardneg_sample_prob=0.35,
        description="Full M10 memory PropRef candidate.",
    ),
    "hard_negative_refresh": PhaseSpec(
        phase="hard_negative_refresh",
        design="D3_HARD_NEGATIVE_REFRESH",
        variant="m10_d3_hierarchical_memory_propref",
        result_dir="results/20260711_srr_v3_m10_hard_negative_refresh",
        min_steps=20000,
        min_train_loop_seconds=5400,
        min_validation_events=10,
        min_full_case_events=4,
        min_eval_cases=44,
        run_label="m10_d3_hard_negative_refresh",
        hardneg_sample_prob=0.45,
        description="Bounded current-model hard-negative refresh.",
    ),
    "no_context_control": PhaseSpec(
        phase="no_context_control",
        design="D3_NO_NNUNET_CONTEXT_CONTROL",
        variant="m10_d3_hierarchical_memory_propref",
        result_dir="results/20260711_srr_v3_m10_no_nnunet_context_control",
        min_steps=20000,
        min_train_loop_seconds=5400,
        min_validation_events=10,
        min_full_case_events=4,
        min_eval_cases=44,
        run_label="m10_d3_no_nnunet_context_control",
        disable_nnunet_anchor=True,
        hardneg_sample_prob=0.35,
        description="D3 retrain with nnU-Net context disabled.",
    ),
    "alignment_control": PhaseSpec(
        phase="alignment_control",
        design="D3_PAIR_VALID_ALIGNMENT_CONTROL",
        variant="m10_d3_hierarchical_memory_propref",
        result_dir="results/20260711_srr_v3_m10_alignment_control",
        min_steps=10000,
        min_train_loop_seconds=3600,
        min_validation_events=8,
        min_full_case_events=3,
        min_eval_cases=44,
        run_label="m10_d3_pair_valid_alignment_control",
        hardneg_sample_prob=0.35,
        alignment_control=True,
        description="Pair-valid alignment train/control placeholder entrypoint.",
    ),
}


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def phase_runtime_root(spec: PhaseSpec) -> Path:
    return REPO_ROOT / spec.result_dir / "runtime"


def make_legacy_args(args: argparse.Namespace, spec: PhaseSpec) -> SimpleNamespace:
    max_steps = args.max_steps or spec.min_steps
    min_seconds = args.min_train_loop_seconds or spec.min_train_loop_seconds
    max_runtime = args.max_runtime_seconds or min(28500.0, float(min_seconds + 1800))
    if max_runtime > 28800:
        raise ValueError("M10 wave 2 jobs must request <=8h runtime budget")
    val_every = args.val_every or max(1, max_steps // spec.min_validation_events)
    hardneg_prob = spec.hardneg_sample_prob if spec.hardneg_sample_prob is not None else 0.30
    if args.hardneg_sample_prob is not None:
        hardneg_prob = args.hardneg_sample_prob
    out_root = Path(args.out_root) if args.out_root else phase_runtime_root(spec)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    return SimpleNamespace(
        variant=spec.variant,
        run_label=args.run_label or spec.run_label,
        fold=args.fold,
        seed=args.seed,
        device=args.device,
        base_channels=args.base_channels,
        encoder_profile=args.encoder_profile,
        patch_shape=args.patch_shape,
        batch_size=args.batch_size,
        max_steps=max_steps,
        max_runtime_seconds=max_runtime,
        out_root=str(out_root),
        nnunet_anchor_root=args.nnunet_anchor_root,
        lr=args.lr,
        weight_decay=args.weight_decay,
        grad_clip=args.grad_clip,
        log_every=args.log_every,
        val_every=val_every,
        min_best_step_fraction=args.min_best_step_fraction,
        early_stop_patience=0,
        early_stop_min_delta=args.early_stop_min_delta,
        min_optimizer_steps_for_plateau=max_steps,
        min_train_loop_seconds_for_plateau=float(min_seconds),
        enforce_min_train_loop_seconds=True,
        complete_oversample=args.complete_oversample,
        oversample_foreground=args.oversample_foreground,
        anatomy_weight=args.anatomy_weight,
        scar_weight=args.scar_weight,
        edema_weight=args.edema_weight,
        proposal_weight=args.proposal_weight,
        margin_weight=args.margin_weight,
        proposal_margin=args.proposal_margin,
        component_proposal_margin=args.component_proposal_margin,
        component_proposal_weight=args.component_proposal_weight,
        semantic_retrieval_weight=args.semantic_retrieval_weight,
        semantic_coverage_weight=args.semantic_coverage_weight,
        semantic_integrative_weight=args.semantic_integrative_weight,
        baseline_preservation_weight=args.baseline_preservation_weight,
        baseline_preservation_confidence=args.baseline_preservation_confidence,
        baseline_gate_harm_weight=args.baseline_gate_harm_weight,
        roi_weight=args.roi_weight,
        roi_remote_weight=args.roi_remote_weight,
        loss_weight_json=args.loss_weight_json,
        loss_weight=args.loss_weight,
        proposal_thresholds=args.proposal_thresholds,
        scar_decode_threshold=args.scar_decode_threshold,
        edema_decode_threshold=args.edema_decode_threshold,
        overfit_steps=args.overfit_steps,
        overfit_log_every=args.overfit_log_every,
        min_overfit_loss_decrease=args.min_overfit_loss_decrease,
        skip_overfit_sanity=args.skip_overfit_sanity,
        prototype_bank_cases=args.prototype_bank_cases,
        skip_prototype_bank_fit=args.skip_prototype_bank_fit,
        max_eval_cases=spec.min_eval_cases,
        eval_case_ids=args.eval_case_ids,
        train_case_ids=args.train_case_ids,
        limit_train_cases=args.limit_train_cases,
        limit_val_cases=args.limit_val_cases,
        hardneg_components_csv=args.hardneg_components_csv,
        hardneg_sample_prob=hardneg_prob,
        variant_config_contract="",
        variant_config_key="",
        disable_local_refinement=args.disable_local_refinement,
        disable_anatomy_roi_prior=args.disable_anatomy_roi_prior,
        disable_nnunet_anchor=bool(args.disable_nnunet_anchor or spec.disable_nnunet_anchor),
        skip_export=args.skip_export,
        variant_config_record={},
    )


def write_phase_contract(spec: PhaseSpec, legacy_args: SimpleNamespace, contract_output_dir: str = "") -> None:
    result_dir = Path(contract_output_dir) if contract_output_dir else REPO_ROOT / spec.result_dir
    if not result_dir.is_absolute():
        result_dir = REPO_ROOT / result_dir
    result_dir.mkdir(parents=True, exist_ok=True)
    contract = {
        "task_key": "20260711_srr_v3_m10_complete_mechanism_repair",
        "executor_id": "m10_myops_training_executor",
        "phase": spec.phase,
        "design": spec.design,
        "variant": spec.variant,
        "run_label": legacy_args.run_label,
        "result_dir": spec.result_dir,
        "runtime_root": legacy_args.out_root,
        "minimums": {
            "optimizer_steps": spec.min_steps,
            "train_loop_seconds": spec.min_train_loop_seconds,
            "validation_events": spec.min_validation_events,
            "full_case_events": spec.min_full_case_events,
            "eval_cases": spec.min_eval_cases,
        },
        "legacy_training_script": "scripts/training/run_srr_propref_myops_fold0.py",
        "legacy_script_edit_policy": "read_or_import_only_not_modified_by_wave2",
        "status": "TRAINING_ENTRYPOINT_STARTED",
    }
    target_name = f"{spec.phase}_m10_phase_contract.json" if contract_output_dir else "m10_phase_contract.json"
    (result_dir / target_name).write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=sorted(PHASES), required=False)
    parser.add_argument("--list-phases", action="store_true")
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--base-channels", type=int, default=32)
    parser.add_argument("--encoder-profile", choices=["tiny_3scale", "strong_4scale", "balanced_4scale", "full_4scale", "safe_4scale"], default="full_4scale")
    parser.add_argument("--patch-shape", default="12,96,96")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-steps", type=_positive_int)
    parser.add_argument("--max-runtime-seconds", type=float)
    parser.add_argument("--min-train-loop-seconds", type=float)
    parser.add_argument("--val-every", type=_positive_int)
    parser.add_argument("--out-root", default="")
    parser.add_argument("--contract-output-dir", default="")
    parser.add_argument("--run-label", default="")
    parser.add_argument("--nnunet-anchor-root", default=str(legacy.DEFAULT_NNUNET_ANCHOR_ROOT))
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--grad-clip", type=float, default=5.0)
    parser.add_argument("--log-every", type=int, default=100)
    parser.add_argument("--min-best-step-fraction", type=float, default=0.20)
    parser.add_argument("--early-stop-min-delta", type=float, default=1e-3)
    parser.add_argument("--complete-oversample", type=float, default=0.55)
    parser.add_argument("--oversample-foreground", type=float, default=0.82)
    parser.add_argument("--anatomy-weight", type=float, default=1.0)
    parser.add_argument("--scar-weight", type=float)
    parser.add_argument("--edema-weight", type=float)
    parser.add_argument("--proposal-weight", type=float)
    parser.add_argument("--margin-weight", type=float, default=0.20)
    parser.add_argument("--proposal-margin", type=float, default=0.20)
    parser.add_argument("--component-proposal-margin", type=float, default=0.35)
    parser.add_argument("--component-proposal-weight", type=float, default=0.20)
    parser.add_argument("--semantic-retrieval-weight", type=float, default=0.04)
    parser.add_argument("--semantic-coverage-weight", type=float, default=0.03)
    parser.add_argument("--semantic-integrative-weight", type=float, default=0.02)
    parser.add_argument("--baseline-preservation-weight", type=float, default=0.0)
    parser.add_argument("--baseline-preservation-confidence", type=float, default=0.80)
    parser.add_argument("--baseline-gate-harm-weight", type=float, default=0.25)
    parser.add_argument("--roi-weight", type=float, default=0.25)
    parser.add_argument("--roi-remote-weight", type=float, default=0.05)
    parser.add_argument("--loss-weight-json", default="")
    parser.add_argument("--loss-weight", action="append", default=[])
    parser.add_argument("--proposal-thresholds", default=legacy.DEFAULT_PROPOSAL_THRESHOLDS)
    parser.add_argument("--scar-decode-threshold", type=float, default=0.50)
    parser.add_argument("--edema-decode-threshold", type=float, default=0.50)
    parser.add_argument("--overfit-steps", type=int, default=40)
    parser.add_argument("--overfit-log-every", type=int, default=10)
    parser.add_argument("--min-overfit-loss-decrease", type=float, default=0.01)
    parser.add_argument("--skip-overfit-sanity", action="store_true")
    parser.add_argument("--prototype-bank-cases", type=int, default=16)
    parser.add_argument("--skip-prototype-bank-fit", action="store_true")
    parser.add_argument("--eval-case-ids", default="")
    parser.add_argument("--train-case-ids", default="")
    parser.add_argument("--limit-train-cases", type=int, default=0)
    parser.add_argument("--limit-val-cases", type=int, default=0)
    parser.add_argument("--hardneg-components-csv", default="results/20260629_proposal_memory_hardneg/mined_components.csv")
    parser.add_argument("--hardneg-sample-prob", type=float)
    parser.add_argument("--disable-local-refinement", action="store_true")
    parser.add_argument("--disable-anatomy-roi-prior", action="store_true")
    parser.add_argument("--disable-nnunet-anchor", action="store_true")
    parser.add_argument("--skip-export", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.list_phases:
        print(json.dumps({key: asdict(value) for key, value in PHASES.items()}, indent=2, sort_keys=True))
        return
    if not args.phase:
        parser.error("--phase is required unless --list-phases is used")
    spec = PHASES[args.phase]
    legacy_args = make_legacy_args(args, spec)
    if args.print_contract:
        print(json.dumps({"phase": asdict(spec), "legacy_args": vars(legacy_args)}, indent=2, sort_keys=True))
        return
    write_phase_contract(spec, legacy_args, args.contract_output_dir)
    legacy.train_variant(legacy_args)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
