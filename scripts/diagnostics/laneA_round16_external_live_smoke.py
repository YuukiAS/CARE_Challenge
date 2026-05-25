#!/usr/bin/env python3
"""Lane A Round16 external live metadata/import/one-case smoke.

This script inspects shallow-cloned external repositories under the Round16
results root. It performs source-level checks only: git HEAD, license file,
requirements, selected py_compile/import attempts, and tiny random tensor
smokes where feasible. It does not download pretrained weights, does not use
external datasets, does not train, and does not create validation packages.
"""

from __future__ import annotations

import csv
import importlib
import os
import py_compile
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"
EXTERNAL_ROOT = OUT_ROOT / "external_repos"


@contextmanager
def sys_path_prepend(path: Path) -> Iterator[None]:
    s = str(path)
    sys.path.insert(0, s)
    try:
        yield
    finally:
        try:
            sys.path.remove(s)
        except ValueError:
            pass


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git_head(path: Path) -> str:
    if not (path / ".git").is_dir():
        return ""
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    except Exception as exc:  # noqa: BLE001
        return f"ERROR:{exc}"


def first_existing(path: Path, names: list[str]) -> Path | None:
    for name in names:
        p = path / name
        if p.is_file():
            return p
    return None


def license_summary(path: Path) -> tuple[str, str]:
    lic = first_existing(path, ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"])
    if not lic:
        return "", "missing"
    text = lic.read_text(encoding="utf-8", errors="ignore")
    first = " ".join(text.splitlines()[:3])[:200]
    lowered = text.lower()
    if "apache license" in lowered:
        status = "apache_like_detected"
    elif "mit license" in lowered:
        status = "mit_like_detected"
    elif "all rights reserved" in lowered:
        status = "restrictive_or_unclear_all_rights_reserved"
    else:
        status = "present_needs_manual_review"
    return str(lic), status + f": {first}"


def requirements_summary(path: Path) -> str:
    req = first_existing(path, ["requirements.txt", "requirements-dev.txt", "environment.yml", "setup.py", "pyproject.toml"])
    if not req:
        return "missing"
    return str(req)


def py_compile_status(path: Path | None) -> str:
    if path is None or not path.is_file():
        return "not_available"
    try:
        py_compile.compile(str(path), doraise=True)
        return "pass"
    except Exception as exc:  # noqa: BLE001
        return f"fail:{type(exc).__name__}:{exc}"[:500]


def import_module_status(repo: Path, module: str) -> str:
    try:
        with sys_path_prepend(repo):
            importlib.invalidate_caches()
            importlib.import_module(module)
        return "pass"
    except Exception as exc:  # noqa: BLE001
        return f"fail:{type(exc).__name__}:{exc}"[:500]


def smoke_inverseform(repo: Path) -> str:
    try:
        with sys_path_prepend(repo):
            mod = importlib.import_module("models.InverseForm")
            model = mod.SmallInverseNet()
            x1 = torch.zeros((1, 1, 112, 112), dtype=torch.float32)
            x2 = torch.zeros((1, 1, 112, 112), dtype=torch.float32)
            out = model(x1, x2)
            assert len(out) == 3
            assert tuple(out[2].shape) == (1, 2)
        return "pass_random_tensor_forward"
    except Exception as exc:  # noqa: BLE001
        return f"fail:{type(exc).__name__}:{exc}"[:500]


def smoke_mednext(repo: Path) -> str:
    try:
        with sys_path_prepend(repo):
            mod = importlib.import_module("nnunet_mednext.network_architecture.mednextv1.create_mednext_v1")
            model = mod.create_mednextv1_small(num_input_channels=3, num_classes=6, kernel_size=3, ds=False)
            param_count = sum(p.numel() for p in model.parameters())
        return f"pass_instantiate_params={param_count}"
    except Exception as exc:  # noqa: BLE001
        return f"fail:{type(exc).__name__}:{exc}"[:500]


def smoke_adamm(repo: Path) -> str:
    try:
        with sys_path_prepend(repo):
            mod = importlib.import_module("models.unet")
            model = mod.UNet3D(input_shape=(16, 16, 16), in_channels=4, out_channels=3, init_channels=8)
            param_count = sum(p.numel() for p in model.parameters())
        return f"pass_instantiate_params={param_count}"
    except Exception as exc:  # noqa: BLE001
        return f"fail:{type(exc).__name__}:{exc}"[:500]


def candidate_specs() -> list[dict[str, object]]:
    return [
        {
            "candidate_id": "R16_B_external_I_MMSeg_metadata_import_onecase",
            "repo_name": "I_MMSeg",
            "url": "https://github.com/zzzzzzl24/I_MMSeg",
            "mechanism": "I_MMSeg_style_T2_LGE_intensity_prior_route",
            "compile_file": "networks/vit_seg_configs.py",
            "import_module": "networks.vit_seg_configs",
            "onecase": "not_run_import_dependency_gate_first",
            "risk_note": "requires ml_collections and ViT/text feature assets; CARE reduction preferred before full repo use",
        },
        {
            "candidate_id": "R16_D_external_CascadedFSN_PTNet_metadata_import_onecase",
            "repo_name": "",
            "url": "",
            "mechanism": "Cascaded_FSN_PTNet_anatomy_pathology_consistency_route",
            "compile_file": "",
            "import_module": "",
            "onecase": "not_available_no_official_repo_identified_in_local_live_smoke",
            "risk_note": "metadata-only; use CARE-first cascade until source/license identified",
        },
        {
            "candidate_id": "R16_G_unime_adamm_copedit_metadata_import_onecase",
            "repo_name": "AdaMM",
            "url": "https://github.com/Quanato607/AdaMM",
            "mechanism": "Missing_modality_representation_route",
            "compile_file": "models/unet.py",
            "import_module": "models.unet",
            "onecase": "adamm",
            "risk_note": "brain/MRI missing-modality distillation assumptions; no CARE teacher proven",
        },
        {
            "candidate_id": "R16_H_pretrained_mednext_or_mms_readiness_smoke",
            "repo_name": "MedNeXt",
            "url": "https://github.com/MIC-DKFZ/MedNeXt",
            "mechanism": "Pretrained_backbone_feature_route",
            "compile_file": "nnunet_mednext/network_architecture/mednextv1/create_mednext_v1.py",
            "import_module": "nnunet_mednext.network_architecture.mednextv1.create_mednext_v1",
            "onecase": "mednext",
            "risk_note": "code can instantiate; pretrained M&Ms weights still need separate data/license audit before use",
        },
        {
            "candidate_id": "R16_I_inverseform_surface_loss_metadata_loss_smoke",
            "repo_name": "InverseForm",
            "url": "https://github.com/Qualcomm-AI-research/InverseForm",
            "mechanism": "Boundary_HD_InverseForm_surface_auxiliary_route",
            "compile_file": "models/InverseForm.py",
            "import_module": "models.InverseForm",
            "onecase": "inverseform",
            "risk_note": "repository is segmentation/geometry oriented; use only as mechanism source for small class_4 auxiliary",
        },
        {
            "candidate_id": "R16_J_caa_seg_ssa_metadata_centerc_smoke",
            "repo_name": "",
            "url": "https://papers.miccai.org/miccai-2025/0009-Paper2655.html",
            "mechanism": "CAA_Seg_SSA_alignment_route",
            "compile_file": "",
            "import_module": "",
            "onecase": "not_available_no_local_code",
            "risk_note": "metadata-only; promote only if CenterC alignment proxy supports it",
        },
        {
            "candidate_id": "R16_K_biomedparse_feature_readiness_smoke",
            "repo_name": "BiomedParse",
            "url": "https://github.com/microsoft/BiomedParse",
            "mechanism": "Pretrained_backbone_feature_route",
            "compile_file": "inference_utils/inference.py",
            "import_module": "inference_utils.inference",
            "onecase": "not_run_weight_and_dependency_gate_first",
            "risk_note": "foundation model needs weights/dependencies; no download or inference in Round16 smoke",
        },
    ]


def run_onecase(spec: dict[str, object], repo: Path) -> str:
    mode = str(spec["onecase"])
    if mode == "inverseform":
        return smoke_inverseform(repo)
    if mode == "mednext":
        return smoke_mednext(repo)
    if mode == "adamm":
        return smoke_adamm(repo)
    return mode


def main() -> None:
    rows: list[dict[str, object]] = []
    for spec in candidate_specs():
        repo_name = str(spec["repo_name"])
        repo = EXTERNAL_ROOT / repo_name if repo_name else Path("")
        repo_available = bool(repo_name and repo.is_dir())
        compile_path = repo / str(spec["compile_file"]) if repo_available and spec["compile_file"] else None
        import_status = "not_available_no_repo" if not repo_available else import_module_status(repo, str(spec["import_module"]))
        compile_status = py_compile_status(compile_path)
        onecase_status = run_onecase(spec, repo) if repo_available else str(spec["onecase"])
        license_path, license_status = license_summary(repo) if repo_available else ("", "not_available")
        status = "pass_import_or_onecase_smoke" if import_status == "pass" or str(onecase_status).startswith("pass") else "metadata_only_or_import_blocked"
        if "fail" in import_status or "fail" in onecase_status:
            status = "import_or_onecase_blocked"
        rows.append(
            {
                "candidate_id": spec["candidate_id"],
                "mechanism": spec["mechanism"],
                "source_url": spec["url"],
                "local_repo_path": str(repo) if repo_available else "",
                "repo_available": repo_available,
                "git_head": git_head(repo) if repo_available else "",
                "license_path": license_path,
                "license_status": license_status,
                "requirements_or_setup": requirements_summary(repo) if repo_available else "",
                "py_compile_status": compile_status,
                "import_status": import_status,
                "onecase_smoke_status": onecase_status,
                "weights_downloaded": "no",
                "external_data_used": "no",
                "care_training_allowed_now": "no" if not str(spec["candidate_id"]).startswith("R16_H") else "no_until_weight_data_license_clear",
                "round16_status": status,
                "risk_note": spec["risk_note"],
            }
        )

    fieldnames = list(rows[0].keys())
    for name in [
        "round16_external_import_smoke_summary.csv",
        "round16_onecase_smoke_summary.csv",
        "round16_onecase_smoke_results.csv",
    ]:
        write_csv(OUT_ROOT / name, rows, fieldnames)
    write_text(
        OUT_ROOT / "round16_external_method_readiness_update.md",
        "# Round16 External Method Readiness Update\n\n"
        "Live metadata/source smoke completed for cloned lightweight repositories. No weights or external data were downloaded.\n\n"
        + "| candidate_id | repo_available | license_status | import_status | onecase_smoke_status | round16_status |\n"
        + "| --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(
            f"| {r['candidate_id']} | {r['repo_available']} | {str(r['license_status']).replace('|', '/')} | {str(r['import_status']).replace('|', '/')} | {str(r['onecase_smoke_status']).replace('|', '/')} | {r['round16_status']} |"
            for r in rows
        )
        + "\n\nTraining remains forbidden for external candidates until license, pretrained data, I/O, and CARE label semantics are explicitly cleared.\n",
    )
    print(f"External live smoke rows: {len(rows)}")


if __name__ == "__main__":
    os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
    main()
