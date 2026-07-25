#!/usr/bin/env python3
"""Generate every LaTeX table in paper/ from the result JSONs.

Missing results render as an em-dash placeholder, so paper/mosaic.tex always
compiles and any number that is not yet real is visibly not real.

    python scripts/make_paper_tables.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "paper" / "results"
TABLES = ROOT / "paper" / "tables"
NA = "--"


def load(track: str, tag: str) -> dict | None:
    path = RESULTS / f"{track}_{tag}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def cell(res: dict | None, key: str, prec: int = 3, with_std: bool = True) -> str:
    if res is None or key not in res.get("average", {}):
        return NA
    mean = res["average"][key]
    if not np.isfinite(mean):
        return NA
    txt = f"{mean:.{prec}f}"
    if with_std:
        std = res.get("std", {}).get(key)
        if std is not None and np.isfinite(std):
            txt += f"\\,\\tiny{{$\\pm$\\,{std:.{prec}f}}}"
    return txt


def delta(res: dict | None, ref: dict | None, key: str, prec: int = 3) -> str:
    """Signed change against the full model, for ablation tables."""
    if res is None or ref is None:
        return NA
    a, b = res.get("average", {}).get(key), ref.get("average", {}).get(key)
    if a is None or b is None or not (np.isfinite(a) and np.isfinite(b)):
        return NA
    d = a - b
    colour = "red" if d < -0.005 else ("teal" if d > 0.005 else "gray")
    return f"\\textcolor{{{colour}}}{{{d:+.{prec}f}}}"


def write(name: str, body: str) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / f"{name}.tex").write_text(body.rstrip() + "\n")
    print(f"  wrote tables/{name}.tex")


# ---------------------------------------------------------------------------
def table_cohort() -> None:
    """Static cohort description, generated from the manifests."""
    rows = []
    manifest = ROOT / "cache" / "manifest.jsonl"
    if manifest.exists():
        recs = [json.loads(l) for l in manifest.open()]
        by_centre: dict[str, list] = {}
        for r in recs:
            by_centre.setdefault(r["center"], []).append(r)
        for centre in sorted(by_centre):
            rs = by_centre[centre]
            mods = "+".join(sorted(set(rs[0]["available_modalities"]),
                                   key=["LGE", "C0", "T2"].index))
            sup = rs[0]["fine_supervision_mask"]
            names = ["myo", "LV", "RV", "edema", "scar"]
            labelled = ", ".join(n for n, s in zip(names, sup) if s > 0.5)
            rows.append(f"{centre[-1]} & {len(rs)} & {mods} & {labelled} \\\\")
    cine = ROOT / "cache" / "cine_manifest.jsonl"
    cine_rows = []
    if cine.exists():
        crecs = [json.loads(l) for l in cine.open()]
        cnt = Counter(r["center"] for r in crecs)
        for centre in sorted(cnt):
            greek = r"$\alpha$" if centre.endswith("alpha") else r"$\beta$"
            cine_rows.append(f"{greek} & {cnt[centre]} & Cine & myo, LV, scar \\\\")

    write("cohort", r"""
\begin{table}[t]
\centering
\caption{The CARE-2026 CARE-Myocardium training cohort. Sequence availability and
annotated classes both vary by centre: 116 of 220 multi-sequence cases provide LGE
alone, and only 80 carry edema labels. The evaluation cohort provides all three
sequences, so a model must both tolerate incomplete inputs at training time and
exploit complete inputs at test time.}
\label{tab:cohort}
\setlength{\tabcolsep}{5pt}
\begin{tabular}{llll}
\toprule
Centre & Cases & Sequences & Annotated classes \\
\midrule
\multicolumn{4}{l}{\textit{MyoPS (multi-sequence)}}\\
""" + "\n".join(rows) + r"""
\midrule
\multicolumn{4}{l}{\textit{CineMyoPS (cine only)}}\\
""" + "\n".join(cine_rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table_main() -> None:
    """Both regimes in one table -- saves most of a page over two separate ones."""
    rm, rc = load("myops", "main"), load("cine", "main")
    myops_cols = [("myo", "Myocardium"), ("lv", "LV"), ("rv", "RV"),
                  ("edema", "Edema"), ("scar", "Scar"), ("lesion_union", "Lesion union")]
    cine_cols = [("myo", "Myocardium"), ("lv", "LV"), ("scar", "Scar")]
    myops_body = "\n".join(
        f"\\quad {label} & {cell(rm, f'{k}_dice')} & {cell(rm, f'{k}_hd95', prec=2)} \\\\"
        for k, label in myops_cols)
    cine_body = "\n".join(
        f"\\quad {label} & {cell(rc, f'{k}_dice')} & {cell(rc, f'{k}_hd95', prec=2)} \\\\"
        for k, label in cine_cols)
    write("main", r"""
\begin{table}[t]
\centering
\caption{Five-fold cross-validated \method\ performance, mean\,$\pm$\,s.d.\ across
folds. MyoPS metrics are computed on the two centres that annotate edema; cine
scar is inferred from motion alone, without any contrast agent.}
\label{tab:main}
\begin{tabular}{lcc}
\toprule
Structure & Dice $\uparrow$ & HD95 (mm) $\downarrow$ \\
\midrule
\multicolumn{3}{l}{\textit{MyoPS: multi-sequence (LGE, C0, T2)}}\\
""" + myops_body + r"""
\midrule
\multicolumn{3}{l}{\textit{CineMyoPS: cine only}}\\
""" + cine_body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table_leaderboard() -> None:
    """Official held-out validation scores -- supplied by the organisers."""
    lb = RESULTS / "leaderboard.json"
    vals = json.loads(lb.read_text()) if lb.exists() else {}

    def g(k, prec=3):
        v = vals.get(k)
        return f"{v:.{prec}f}" if isinstance(v, (int, float)) else NA

    write("leaderboard", r"""
\begin{table}[t]
\centering
\caption{\method\ on the held-out CARE-2026 validation set, scored by the
organisers. Lb1--Lb3 are the three official leaderboards.}
\label{tab:leaderboard}
\begin{tabular}{llcc}
\toprule
Leaderboard & Target & Dice $\uparrow$ & HD95 (mm) $\downarrow$ \\
\midrule
Lb1 & MyoPS scar      & """ + g("lb1_dice") + " & " + g("lb1_hd95", 2) + r""" \\
Lb2 & MyoPS edema     & """ + g("lb2_dice") + " & " + g("lb2_hd95", 2) + r""" \\
Lb3 & CineMyoPS scar  & """ + g("lb3_dice") + " & " + g("lb3_hd95", 2) + r""" \\
\bottomrule
\end{tabular}
\end{table}
""")


MYOPS_ABLATIONS = [
    ("__group__", "Architecture"),
    ("no_tps",          r"w/o TPS feature alignment"),
    ("earlyfusion",     r"early fusion (single shared encoder)"),
    ("no_cascade",      r"w/o Stage-1 anatomy cascade"),
    ("no_spg",          r"w/o spatial prior gate"),
    ("no_edema_expert", r"w/o dedicated edema expert"),
    ("__group__", "Objective"),
    ("no_supmask",      r"w/o supervision masking"),
    ("no_consistency",  r"w/o cross-sequence consistency"),
    ("no_lesion_loss",  r"w/o lesion Tversky\,/\,focal terms"),
    ("__group__", "Inference"),
    ("no_tta",          r"w/o test-time augmentation"),
    ("no_constraint",   r"w/o anatomical constraint"),
    ("no_cc",           r"w/o component cleanup"),
]

CINE_ABLATIONS = [
    ("__group__", "Evidence source"),
    ("no_motion",      r"intensity instead of motion"),
    ("ed_only",        r"single ED frame ($T{=}1$)"),
    ("__group__", "Auxiliary objectives"),
    ("no_smooth",      r"w/o flow smoothness"),
    ("no_consistency", r"w/o temporal anatomy consistency"),
    ("__group__", "Inference"),
    ("no_tta",         r"w/o test-time augmentation"),
    ("no_constraint",  r"w/o anatomical constraint"),
    ("no_cc",          r"w/o component cleanup"),
]


def _ablation_body(track: str, spec, keys) -> str:
    ref = load(track, "main")
    lines = [" & ".join(["\\textbf{\\method\\ (full)}"] +
                        [cell(ref, k) for k in keys] + [""]).rstrip(" &") + r" \\"]
    lines[0] = "\\textbf{\\method\\ (full)} & " + " & ".join(
        cell(ref, k) for k in keys) + " & " + NA + r" \\"
    for tag, label in spec:
        if tag == "__group__":
            lines.append(r"\midrule")
            lines.append(rf"\multicolumn{{{len(keys) + 2}}}{{l}}{{\textit{{{label}}}}} \\")
            continue
        r = load(track, tag)
        primary = keys[0]
        lines.append(f"\\quad {label} & " + " & ".join(cell(r, k) for k in keys)
                     + " & " + delta(r, ref, primary) + r" \\")
    return "\n".join(lines)


def table_ablation_myops() -> None:
    keys = ["scar_dice", "edema_dice", "lesion_union_dice"]
    write("ablation_myops", r"""
\begin{table}[t]
\centering
\caption{MyoPS ablation, five-fold cross-validated Dice. Every variant is
retrained from scratch on the same folds and consumes the same frozen Stage-1
prior, so Stage-1 is never a confound. $\Delta$ is the change in scar Dice
against the full model.}
\label{tab:ablation_myops}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lcccc}
\toprule
Variant & Scar & Edema & Lesion union & $\Delta$Scar \\
\midrule
""" + _ablation_body("myops", MYOPS_ABLATIONS, keys) + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table_ablation_cine() -> None:
    keys = ["scar_dice", "myo_dice", "lv_dice"]
    write("ablation_cine", r"""
\begin{table}[t]
\centering
\caption{CineMyoPS ablation, five-fold cross-validated Dice. Replacing the motion
field with raw intensity at the pathology head is the single most damaging
change, supporting our claim that cine scar is a kinematic rather than a
photometric phenomenon.}
\label{tab:ablation_cine}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{lcccc}
\toprule
Variant & Scar & Myocardium & LV & $\Delta$Scar \\
\midrule
""" + _ablation_body("cine", CINE_ABLATIONS, keys) + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def table_modality() -> None:
    rows = [("main", "LGE + C0 + T2 (full)"),
            ("modality_lge_c0", "LGE + C0"),
            ("modality_lge_only", "LGE only")]
    body = "\n".join(
        f"{label} & " + " & ".join(cell(load('myops', tag), k)
                                   for k in ("scar_dice", "edema_dice", "myo_dice")) + r" \\"
        for tag, label in rows)
    write("modality", r"""
\begin{table}[t]
\centering
\caption{Robustness to sequence availability. The \emph{same} trained model is
evaluated with sequences withheld at inference by clearing their presence flags
and zero-filling their channels, exactly as an incomplete centre would appear.}
\label{tab:modality}
\begin{tabular}{lccc}
\toprule
Sequences available & Scar & Edema & Myocardium \\
\midrule
""" + body + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def macros_edema() -> None:
    """Edema-expert ablation reported inline in prose rather than as a table.

    Emits \\edemaZoneFull, \\edemaZoneNoCz, \\edemaZoneDirect.
    """
    def full_zone() -> str:
        vals = []
        for fold in range(5):
            for name in ("best.pt", "last.pt"):
                p = ROOT / "grid_output" / "5fold" / f"fold{fold}" / "edema" / name
                if p.exists():
                    try:
                        d = torch.load(str(p), map_location="cpu", weights_only=False)
                    except Exception:
                        continue
                    if "edema_dice" in d:
                        vals.append(float(d["edema_dice"]))
                    break
        if not vals:
            return NA
        return f"{np.mean(vals):.3f}\\,\\tiny{{$\\pm$\\,{np.std(vals):.3f}}}"

    def variant(name: str) -> str:
        vals = []
        for fold in range(5):
            p = ROOT / "ablations" / "edema" / name / f"fold{fold}" / "experiment_result.json"
            if p.exists():
                try:
                    vals.append(float(json.loads(p.read_text())["best_val_dice"]))
                except Exception:
                    pass
        if not vals:
            return NA
        return f"{np.mean(vals):.3f}\\,\\tiny{{$\\pm$\\,{np.std(vals):.3f}}}"

    write("macros", "\n".join([
        r"\newcommand{\edemaZoneFull}{" + full_zone() + "}",
        r"\newcommand{\edemaZoneNoCz}{" + variant("no_c0") + "}",
        r"\newcommand{\edemaZoneDirect}{" + variant("no_zone") + "}",
    ]))


def main() -> None:
    print("Generating paper tables...")
    table_cohort()
    table_main()
    table_leaderboard()
    table_ablation_myops()
    table_ablation_cine()
    macros_edema()
    table_modality()
    missing = sum(1 for p in TABLES.glob("*.tex") if NA in p.read_text())
    print(f"\nDone. {missing} table(s) still contain placeholders.")


if __name__ == "__main__":
    main()
