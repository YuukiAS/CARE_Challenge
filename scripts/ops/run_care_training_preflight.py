#!/usr/bin/env python3
"""Run a CARE training environment preflight and write a JSON receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def run(cmd: list[str] | str, shell: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, shell=shell, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def check_import(python: str, module: str) -> dict[str, object]:
    cp = run([python, "-c", f"import {module}"])
    return {"module": module, "exit_code": cp.returncode, "stderr_tail": cp.stderr[-1000:]}


def optimizer_smoke(python: str, mode: str) -> dict[str, object]:
    if mode.lower() != "adamw":
        return {"mode": mode, "status": "skipped"}
    code = "import torch; p=torch.nn.Parameter(torch.ones(())); torch.optim.AdamW([p], lr=1e-4); print('PASS')"
    cp = run([python, "-c", code])
    return {"mode": mode, "exit_code": cp.returncode, "stdout_tail": cp.stdout[-1000:], "stderr_tail": cp.stderr[-1000:]}


def writable(path: Path, directory: bool = False) -> dict[str, object]:
    target = path if directory else path.parent
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".care_preflight_write_probe"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        return {"path": str(target), "writable": True}
    except OSError as exc:
        return {"path": str(target), "writable": False, "error": str(exc)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True)
    parser.add_argument("--entrypoint", required=True)
    parser.add_argument("--config")
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--log-dir", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument("--import", dest="imports", action="append", default=[])
    parser.add_argument("--optimizer-smoke-command", default="adamw")
    parser.add_argument("--contract-command", default="")
    parser.add_argument("--receipt-path", required=True, type=Path)
    args = parser.parse_args(argv)

    python_path = Path(args.python)
    entrypoint = Path(args.entrypoint)
    config = Path(args.config) if args.config else None
    receipt: dict[str, object] = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": str(python_path),
        "python_exists": python_path.exists(),
        "python_version": "",
        "entrypoint": str(entrypoint),
        "entrypoint_hash": sha256_path(entrypoint),
        "config": str(config) if config else "",
        "config_hash": sha256_path(config) if config else "",
        "code_hash": sha256_path(entrypoint),
        "split_hash": "",
        "imports": {},
        "optimizer_smoke": {},
        "cuda_visible": None,
        "path_writability": {},
        "contract_command": args.contract_command,
        "contract_exit_code": None,
        "exit_code": 0,
    }
    version = run([str(python_path), "--version"])
    receipt["python_version"] = (version.stdout or version.stderr).strip()
    if version.returncode != 0:
        receipt["exit_code"] = 1
    import_results = {module: check_import(str(python_path), module) for module in args.imports}
    receipt["imports"] = import_results
    if any(item["exit_code"] != 0 for item in import_results.values()):
        receipt["exit_code"] = 1
    smoke = optimizer_smoke(str(python_path), args.optimizer_smoke_command)
    receipt["optimizer_smoke"] = smoke
    if smoke.get("exit_code", 0) != 0:
        receipt["exit_code"] = 1
    cuda = run([str(python_path), "-c", "import torch; print(torch.cuda.is_available())"])
    receipt["cuda_visible"] = cuda.stdout.strip() == "True" if cuda.returncode == 0 else None
    receipt["path_writability"] = {
        "result_dir": writable(args.result_dir, directory=True),
        "log_dir": writable(args.log_dir, directory=True),
        "lock_parent": writable(args.lock_path),
    }
    if any(not item["writable"] for item in dict(receipt["path_writability"]).values()):
        receipt["exit_code"] = 1
    if args.contract_command:
        cp = run(args.contract_command, shell=True)
        receipt["contract_exit_code"] = cp.returncode
        receipt["contract_stdout_tail"] = cp.stdout[-2000:]
        receipt["contract_stderr_tail"] = cp.stderr[-2000:]
        if cp.returncode != 0:
            receipt["exit_code"] = 1
    args.receipt_path.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.receipt_path)
    return int(receipt["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
