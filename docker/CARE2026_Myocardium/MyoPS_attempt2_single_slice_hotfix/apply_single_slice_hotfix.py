from __future__ import annotations

import hashlib
import importlib
import importlib.metadata as metadata
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_VERSION = "2.7.0"
EXPECTED_SOURCE_SHA256 = "0925abcba8f87d84819921ae661fdafa5c871226a5dbceca61e9947e63acad98"
MODULE = "nnunetv2.preprocessing.resampling.default_resampling"
ORIGINAL = """new_shape = np.array([int(round(i / j * k)) for i, j, k in zip(old_spacing, new_spacing, old_shape)])
    return new_shape"""
PATCHED = """new_shape = np.array([int(round(i / j * k)) for i, j, k in zip(old_spacing, new_spacing, old_shape)])
    new_shape = np.maximum(new_shape, 1)
    return new_shape"""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    version = metadata.version("nnunetv2")
    if version != EXPECTED_VERSION:
        raise RuntimeError(f"nnunetv2 version mismatch: {version} != {EXPECTED_VERSION}")

    module = importlib.import_module(MODULE)
    source_path = Path(inspect.getsourcefile(module) or "").resolve()
    if not source_path.exists():
        raise RuntimeError(f"Cannot locate nnU-Net source for {MODULE}")

    original_bytes = source_path.read_bytes()
    original_sha = sha256_bytes(original_bytes)
    if original_sha != EXPECTED_SOURCE_SHA256:
        raise RuntimeError(
            f"nnU-Net source SHA mismatch: {original_sha} != {EXPECTED_SOURCE_SHA256}"
        )

    text = original_bytes.decode("utf-8")
    replacement_count = text.count(ORIGINAL)
    if replacement_count != 1:
        raise RuntimeError(f"Expected source pattern exactly once, found {replacement_count}")

    patched_text = text.replace(ORIGINAL, PATCHED, 1)
    source_path.write_text(patched_text, encoding="utf-8")
    compile(patched_text, str(source_path), "exec")
    importlib.invalidate_caches()
    patched_module = importlib.reload(module)
    patched_source = inspect.getsource(patched_module.compute_new_shape)
    if "np.maximum(new_shape, 1)" not in patched_source:
        raise RuntimeError("Patched compute_new_shape does not contain minimum-one clamp")

    patched_sha = sha256_bytes(source_path.read_bytes())
    receipt = {
        "package": "nnunetv2",
        "version": version,
        "module": MODULE,
        "source_path": str(source_path),
        "original_source_sha256": original_sha,
        "patched_source_sha256": patched_sha,
        "replacement_count": replacement_count,
        "patch": {
            "removed": ORIGINAL,
            "added": PATCHED,
        },
        "patched_function_source": patched_source,
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    receipt_path = Path("/app/hotfix/single_slice_hotfix_receipt.json")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
