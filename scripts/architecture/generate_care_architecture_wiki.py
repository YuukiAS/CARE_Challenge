#!/usr/bin/env python3
"""Generate and check CARE architecture wiki diagram artifacts."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


FIGURES = (
    "model-current",
    "model-gap",
    "execution-flow",
)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def render_one(repo_root: Path, stem: str, check: bool) -> list[str]:
    figure_dir = repo_root / "wiki" / "figures"
    d2_path = figure_dir / f"{stem}.d2"
    svg_path = figure_dir / f"{stem}.svg"
    png_path = figure_dir / f"{stem}.png"
    errors: list[str] = []

    if not d2_path.is_file():
        return [f"missing D2 source: {d2_path}"]

    if check:
        for output in (svg_path, png_path):
            if not output.is_file():
                errors.append(f"missing rendered artifact: {output}")
            elif output.stat().st_mtime < d2_path.stat().st_mtime:
                errors.append(f"rendered artifact is older than D2 source: {output}")
        return errors

    d2 = shutil.which("d2")
    if not d2:
        return ["d2 executable not found"]
    convert = shutil.which("convert")

    cp = run([d2, str(d2_path), str(svg_path)], repo_root)
    if cp.returncode != 0:
        errors.append(f"d2 svg render failed for {d2_path}: {cp.stderr.strip() or cp.stdout.strip()}")
        return errors

    cp = run([d2, str(d2_path), str(png_path)], repo_root)
    if cp.returncode == 0:
        return errors

    if not convert:
        errors.append(f"d2 png render failed and ImageMagick convert is unavailable: {cp.stderr.strip()}")
        return errors

    cp2 = run([convert, str(svg_path), str(png_path)], repo_root)
    if cp2.returncode != 0:
        errors.append(
            "png render failed: d2 error="
            + (cp.stderr.strip() or cp.stdout.strip())
            + "; convert error="
            + (cp2.stderr.strip() or cp2.stdout.strip())
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check artifacts without rendering.")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    required_inputs = [repo_root / "wiki" / "architecture.yaml", repo_root / "wiki" / "COMPONENTS.csv"]
    errors = [f"missing required input: {path}" for path in required_inputs if not path.is_file()]
    for stem in FIGURES:
        errors.extend(render_one(repo_root, stem, check=args.check))

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("care architecture wiki diagrams ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
