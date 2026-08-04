#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch
from nnunetv2.inference.predict_from_raw_data import (
    nnUNetPredictor,
    convert_predicted_logits_to_segmentation_with_correct_shape,
)

APP = Path(__file__).resolve().parent
INPUT_DIR = Path(os.environ.get("CARE_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("CARE_OUTPUT_DIR", "/output/myops"))
NNUNET_RESULTS = Path(os.environ.get("nnUNet_results", APP / "models/nnunet/nnUNet_results"))
NNUNET_RAW = Path(os.environ.get("nnUNet_raw", APP / "models/nnunet/nnUNet_raw"))
NNUNET_PREPROCESSED = Path(os.environ.get("nnUNet_preprocessed", APP / "models/nnunet/nnUNet_preprocessed"))
SELF_MODEL_DIR = Path(os.environ.get("CARE_SELF_MODEL_DIR", APP / "models/self_model"))
CARE_SRC = APP / "src"
if CARE_SRC.exists() and str(CARE_SRC) not in sys.path:
    sys.path.insert(0, str(CARE_SRC))

CHANNELS = (("LGE", 0), ("T2", 1), ("C0", 2))
OFFICIAL_LABELS = {
    0: 0,
    1: 200,
    2: 500,
    3: 600,
    4: 1220,
    5: 2221,
}


def discover_cases(input_dir: Path) -> list[tuple[str, dict[str, Path]]]:
    search_root = input_dir if input_dir.exists() else Path("/input")
    lge_files = sorted(search_root.glob("**/*_LGE.nii.gz"))
    cases: list[tuple[str, dict[str, Path]]] = []
    errors: list[str] = []

    for lge_path in lge_files:
        case_id = lge_path.name.removesuffix("_LGE.nii.gz")
        case_dir = lge_path.parent
        modalities = {"LGE": lge_path}
        missing = []
        for modality, _ in CHANNELS:
            candidate = case_dir / f"{case_id}_{modality}.nii.gz"
            if candidate.exists():
                modalities[modality] = candidate
            else:
                missing.append(modality)
        if missing:
            errors.append(f"{case_id}: missing modalities {','.join(missing)} in {case_dir}")
        else:
            cases.append((case_id, modalities))

    if not lge_files:
        raise RuntimeError(f"No MyoPS LGE inputs found under {search_root}")
    if errors:
        raise RuntimeError("Incomplete MyoPS input cases:\n" + "\n".join(errors))
    return sorted(cases, key=lambda item: item[0])


def prepare_nnunet_input(cases: list[tuple[str, dict[str, Path]]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for case_id, modalities in cases:
        for modality, channel in CHANNELS:
            shutil.copy2(modalities[modality], out_dir / f"{case_id}_{channel:04d}.nii.gz")


def run_nnunet(in_dir: Path, out_dir: Path) -> None:
    device = os.environ.get("CARE_DEVICE", "cpu")
    cmd = [
        "nnUNetv2_predict",
        "-d",
        "501",
        "-tr",
        "nnUNetTrainer_500epochs",
        "-c",
        "3d_fullres",
        "-f",
        "0",
        "1",
        "2",
        "3",
        "4",
        "-chk",
        "checkpoint_best.pth",
        "-i",
        str(in_dir),
        "-o",
        str(out_dir),
        "-npp",
        "1",
        "-nps",
        "1",
        "-device",
        device,
        "--disable_progress_bar",
    ]
    env = os.environ.copy()
    env["nnUNet_results"] = str(NNUNET_RESULTS)
    env["nnUNet_raw"] = str(NNUNET_RAW)
    env["nnUNet_preprocessed"] = str(NNUNET_PREPROCESSED)
    subprocess.run(cmd, check=True, env=env)


def load_self_model_selection() -> dict | None:
    path = SELF_MODEL_DIR / "selection.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not payload.get("enabled", True):
        return None
    if payload.get("kind") != "care_ase":
        raise RuntimeError(f"Unsupported self-model selection kind: {payload.get('kind')}")
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        raise RuntimeError("CARE self-model selection requires a non-empty checkpoints list")
    for item in checkpoints:
        ckpt = SELF_MODEL_DIR / str(item["checkpoint"])
        sidecar = ckpt.with_suffix(ckpt.suffix + ".sha256")
        if not ckpt.is_file() or not sidecar.is_file():
            raise RuntimeError(f"Missing CARE-ASE checkpoint or sidecar: {ckpt}")
        plans = SELF_MODEL_DIR / str(item.get("plans", "nnUNetPlans.json"))
        if not plans.is_file():
            raise RuntimeError(f"Missing CARE-ASE plans file: {plans}")
    return payload


def build_preprocessing_predictor(device: torch.device) -> nnUNetPredictor:
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=device.type == "cuda",
        device=device,
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(
        str(NNUNET_RESULTS / "Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"),
        use_folds=(0,),
        checkpoint_name="checkpoint_best.pth",
    )
    return predictor


def preprocess_for_care(
    predictor: nnUNetPredictor,
    case_id: str,
    modalities: dict[str, Path],
    tmp: Path,
) -> tuple[torch.Tensor, dict]:
    input_files = [[str(modalities[modality]) for modality, _ in CHANNELS]]
    out_stub = [str(tmp / f"{case_id}_care_preprocess_stub")]
    iterator = predictor._internal_get_data_iterator_from_lists_of_filenames(input_files, None, out_stub, 1)
    item = next(iterator)
    data = item["data"]
    if not torch.is_tensor(data):
        data = torch.from_numpy(np.asarray(data))
    if data.ndim != 4:
        raise RuntimeError(f"{case_id}: expected preprocessed CARE data [C,Z,Y,X], got {tuple(data.shape)}")
    return data.float(), item["data_properties"]


def run_care_ase_raw_prediction(
    selection: dict,
    predictor: nnUNetPredictor,
    case_id: str,
    modalities: dict[str, Path],
    tmp: Path,
    device: torch.device,
) -> np.ndarray:
    from src.care_myocardium.inference.care_ase_r2_full_volume import (
        CAREASEFullVolumeInferenceSettings,
        predict_care_ase_r2_full_volume_logits,
    )
    from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference

    data, properties = preprocess_for_care(predictor, case_id, modalities, tmp)
    image = data[None].to(device=device, dtype=torch.float32)
    availability = torch.ones((1, 3), device=device, dtype=torch.float32)
    settings_payload = dict(selection.get("inference_settings") or {})
    settings = CAREASEFullVolumeInferenceSettings(
        patch_size=tuple(int(v) for v in settings_payload.get("patch_size", (20, 256, 256))),
        tile_step_size=float(settings_payload.get("tile_step_size", 0.5)),
        use_gaussian=bool(settings_payload.get("use_gaussian", True)),
        gaussian_sigma_scale=float(settings_payload.get("gaussian_sigma_scale", 1.0 / 8.0)),
        use_mirroring=bool(settings_payload.get("use_mirroring", True)),
        allowed_mirror_axes=tuple(int(v) for v in settings_payload.get("allowed_mirror_axes", (0, 1, 2))),
        precision="fp32",
    )
    logits_sum = None
    loaded_count = 0
    with torch.no_grad():
        for item in selection["checkpoints"]:
            ckpt = SELF_MODEL_DIR / str(item["checkpoint"])
            plans = SELF_MODEL_DIR / str(item.get("plans", "nnUNetPlans.json"))
            model, payload = load_care_ase_checkpoint_for_inference(ckpt, map_location=device, plans_path=plans)
            model.to(device).eval()
            global_step = int(item.get("global_step", payload.get("global_optimizer_step", selection.get("global_step", 14000))))
            logits = predict_care_ase_r2_full_volume_logits(
                model,
                image,
                availability,
                settings=settings,
                global_step=global_step,
            )[0].detach().cpu()
            logits_sum = logits if logits_sum is None else logits_sum + logits
            loaded_count += 1
    if logits_sum is None or loaded_count == 0:
        raise RuntimeError("CARE-ASE selection did not produce logits")
    logits_mean = logits_sum / float(loaded_count)
    raw = convert_predicted_logits_to_segmentation_with_correct_shape(
        logits_mean,
        predictor.plans_manager,
        predictor.configuration_manager,
        predictor.label_manager,
        properties,
        return_probabilities=False,
    )
    return np.asarray(raw, dtype=np.uint8)


def apply_self_model_overlay(
    nnunet_raw: np.ndarray,
    care_raw: np.ndarray,
    selection: dict,
) -> np.ndarray:
    if tuple(nnunet_raw.shape) != tuple(care_raw.shape):
        raise RuntimeError(f"CARE-ASE raw shape {care_raw.shape} does not match nnU-Net raw shape {nnunet_raw.shape}")
    out = np.asarray(nnunet_raw, dtype=np.uint8).copy()
    if bool(selection.get("edema_enabled", True)):
        out[care_raw == 4] = 4
    if bool(selection.get("scar_enabled", True)):
        out[care_raw == 5] = 5
    return out


def map_to_official_labels(raw_path: Path, final_path: Path, raw_override: np.ndarray | None = None) -> None:
    image = sitk.ReadImage(str(raw_path))
    raw = raw_override if raw_override is not None else sitk.GetArrayFromImage(image)
    raw_values = set(np.unique(raw).astype(int).tolist())
    unexpected = sorted(raw_values.difference(OFFICIAL_LABELS))
    if unexpected:
        raise RuntimeError(f"{raw_path.name}: unexpected nnU-Net labels {unexpected}")

    final = np.zeros(raw.shape, dtype=np.int16)
    for raw_label, official_label in OFFICIAL_LABELS.items():
        if official_label:
            final[raw == raw_label] = official_label

    out_image = sitk.GetImageFromArray(final)
    out_image.CopyInformation(image)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = final_path.with_name(f".{final_path.name.removesuffix('.nii.gz')}.tmp.nii.gz")
    sitk.WriteImage(out_image, str(tmp_path))
    os.replace(tmp_path, final_path)


def main() -> int:
    try:
        cases = discover_cases(INPUT_DIR)
        print(f"Found {len(cases)} complete MyoPS cases under {INPUT_DIR}")
        selection = load_self_model_selection()
        if selection:
            print(f"Using CARE self-model overlay from {SELF_MODEL_DIR / 'selection.json'}")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="care_myops_nnunet_") as tmpdir:
            tmp = Path(tmpdir)
            nnunet_in = tmp / "input"
            nnunet_out = tmp / "output"
            prepare_nnunet_input(cases, nnunet_in)
            run_nnunet(nnunet_in, nnunet_out)
            device = torch.device(os.environ.get("CARE_DEVICE", "cpu"))
            care_preprocessor = build_preprocessing_predictor(device) if selection else None
            for case_id, _ in cases:
                raw_path = nnunet_out / f"{case_id}.nii.gz"
                if not raw_path.exists():
                    raise RuntimeError(f"{case_id}: nnU-Net did not produce {raw_path}")
                raw_override = None
                if selection and care_preprocessor is not None:
                    modalities = dict(cases)[case_id]
                    nnunet_raw = sitk.GetArrayFromImage(sitk.ReadImage(str(raw_path)))
                    care_raw = run_care_ase_raw_prediction(selection, care_preprocessor, case_id, modalities, tmp, device)
                    raw_override = apply_self_model_overlay(nnunet_raw, care_raw, selection)
                map_to_official_labels(raw_path, OUTPUT_DIR / f"{case_id}_pred.nii.gz", raw_override=raw_override)
                print(f"{case_id}: wrote {OUTPUT_DIR / f'{case_id}_pred.nii.gz'}")
    except Exception as exc:
        print(f"CARE MyoPS inference failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
