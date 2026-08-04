#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CARE_ROOT = Path(__file__).resolve().parents[2]
MYOPS_CONTEXT = CARE_ROOT / "docker/CARE2026_Myocardium/MyoPS"
NNUNET_ASSET_ROOT = CARE_ROOT / (
    "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
DATASET_ROOT = CARE_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
DEFAULT_OUTPUT_ROOT = (
    Path("/users/a/e/aereinh/.tmp/codex-CARE")
    / "20260804_care_ase_r2_deadline_recovery_training_docker"
    / "attempt3_docker_transfer"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {"__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}}

    shutil.copytree(src, dst, ignore=ignore)


def deterministic_tar_gz(src_dir: Path, out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    with out_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for path in sorted(src_dir.rglob("*")):
                    arcname = path.relative_to(src_dir).as_posix()
                    info = tar.gettarinfo(str(path), arcname=arcname)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if path.is_file():
                        with path.open("rb") as f:
                            tar.addfile(info, f)
                    else:
                        tar.addfile(info)


def list_files(root: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return files


def copy_nnunet_models(context_dst: Path) -> list[dict[str, Any]]:
    model_dst = context_dst / "models/nnunet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
    model_dst.mkdir(parents=True, exist_ok=True)
    for name in ("plans.json", "dataset.json"):
        shutil.copy2(NNUNET_ASSET_ROOT / name, model_dst / name)
    for fold in range(5):
        dst = model_dst / f"fold_{fold}"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(NNUNET_ASSET_ROOT / f"fold_{fold}/checkpoint_best.pth", dst / "checkpoint_best.pth")
    (context_dst / "models/nnunet/nnUNet_raw").mkdir(parents=True, exist_ok=True)
    (context_dst / "models/nnunet/nnUNet_preprocessed").mkdir(parents=True, exist_ok=True)
    return list_files(context_dst / "models/nnunet")


def copy_care_runtime(context_dst: Path) -> list[dict[str, Any]]:
    vendor_src = context_dst / "care_ase_vendor/src/src"
    copytree_clean(CARE_ROOT / "src", vendor_src)
    dataset_dst = context_dst / "care_ase_vendor/data/data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
    dataset_dst.mkdir(parents=True, exist_ok=True)
    for name in ("nnUNetPlans.json", "dataset.json"):
        shutil.copy2(DATASET_ROOT / name, dataset_dst / name)
    return list_files(context_dst / "care_ase_vendor")


def copy_self_model_selection(selection_path: Path, context_dst: Path) -> dict[str, Any]:
    source = json.loads(selection_path.read_text(encoding="utf-8"))
    if source.get("kind") != "care_ase":
        raise RuntimeError("attempt3 MyoPS bundle only supports kind=care_ase")
    dst_dir = context_dst / "models/self_model"
    dst_dir.mkdir(parents=True, exist_ok=True)
    rewritten = dict(source)
    rewritten_checkpoints = []
    copied = []
    for idx, item in enumerate(source.get("checkpoints", []), start=1):
        src_ckpt = Path(item["checkpoint"]).expanduser()
        if not src_ckpt.is_absolute():
            src_ckpt = (selection_path.parent / src_ckpt).resolve()
        src_sidecar = src_ckpt.with_suffix(src_ckpt.suffix + ".sha256")
        if not src_ckpt.is_file() or not src_sidecar.is_file():
            raise FileNotFoundError(f"missing selected checkpoint or sidecar: {src_ckpt}")
        ckpt_name = f"care_ase_{idx:02d}_{src_ckpt.name}"
        shutil.copy2(src_ckpt, dst_dir / ckpt_name)
        shutil.copy2(src_sidecar, (dst_dir / ckpt_name).with_suffix((dst_dir / ckpt_name).suffix + ".sha256"))
        plans_src = Path(item.get("plans", DATASET_ROOT / "nnUNetPlans.json")).expanduser()
        if not plans_src.is_absolute():
            plans_src = (selection_path.parent / plans_src).resolve()
        plans_name = f"care_ase_{idx:02d}_nnUNetPlans.json"
        shutil.copy2(plans_src, dst_dir / plans_name)
        copied.append(
            {
                "source_checkpoint": str(src_ckpt),
                "bundled_checkpoint": f"models/self_model/{ckpt_name}",
                "checkpoint_sha256": sha256_file(src_ckpt),
                "bundled_plans": f"models/self_model/{plans_name}",
                "plans_sha256": sha256_file(plans_src),
            }
        )
        new_item = dict(item)
        new_item["checkpoint"] = ckpt_name
        new_item["plans"] = plans_name
        rewritten_checkpoints.append(new_item)
    if not rewritten_checkpoints:
        raise RuntimeError("selection contains no checkpoints")
    rewritten["checkpoints"] = rewritten_checkpoints
    write_json(dst_dir / "selection.json", rewritten)
    return {
        "selection_path": str(selection_path),
        "selection_sha256": sha256_file(selection_path),
        "bundled_selection": "models/self_model/selection.json",
        "bundled_selection_sha256": sha256_file(dst_dir / "selection.json"),
        "copied": copied,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-json", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    bundle_root = output_root / "workstation_bundle_root"
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.mkdir(parents=True)
    context_dst = bundle_root / "contexts/MyoPS"
    copytree_clean(MYOPS_CONTEXT, context_dst)
    nnunet_manifest = copy_nnunet_models(context_dst)
    care_manifest = copy_care_runtime(context_dst)
    selection_manifest = copy_self_model_selection(args.selection_json.resolve(), context_dst)

    readme = bundle_root / "README.md"
    readme.write_text(
        """# CARE2026 MyoPS Attempt3 Self-Model Bundle

Build:

```bash
cd contexts/MyoPS
docker build -t care-myocardium-myops:attempt3 .
```

Run with official-style input mounted at `/input` and output at `/output`.
The context uses nnU-Net for anatomy/geometry and the selected CARE-ASE
self-model checkpoint(s) for requested scar/edema raw-label overlay.
""",
        encoding="utf-8",
    )
    archive = output_root / "MyoPS-attempt3-self-model-workstation-bundle.tar.gz"
    deterministic_tar_gz(bundle_root, archive)
    (archive.with_suffix(archive.suffix + ".sha256")).write_text(
        f"{sha256_file(archive)}  {archive.name}\n",
        encoding="utf-8",
    )
    manifest = {
        "status": "READY",
        "created_at_utc": now(),
        "bundle_path": str(archive),
        "bundle_sha256": sha256_file(archive),
        "bundle_size_bytes": archive.stat().st_size,
        "context_path_in_bundle": "contexts/MyoPS",
        "nnunet_file_count": len(nnunet_manifest),
        "care_runtime_file_count": len(care_manifest),
        "selection": selection_manifest,
        "all_files": list_files(bundle_root),
    }
    write_json(output_root / "attempt3_bundle_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
