#!/usr/bin/env python
"""Draw the SRR-MyoPS method overview figure.

Run from the repository root:
    ./envs/env_CARE/bin/python results/figures/srr_myops_architecture.py
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(os.environ.get("TMPDIR", "/tmp")) / "care_srr_myops_mplconfig"),
)

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT_DIR = Path(__file__).resolve().parent
BASE = OUT_DIR / "srr_myops_architecture"


COLORS = {
    "input": "#D8EAF8",
    "stem": "#E9F2FB",
    "encoder": "#F2F6FA",
    "router": "#FFF3D8",
    "bank": "#F5E6FB",
    "decoder": "#E7F4E7",
    "prior": "#FCE3D9",
    "loss": "#F4F0E8",
    "optional": "#F5F5F5",
    "cine": "#E6F2F0",
    "edge": "#243447",
    "muted": "#6D7780",
    "ana": "#2F7D32",
    "scar": "#B0413E",
    "ede": "#2F6FB0",
}


POS = {
    "title": (8.0, 8.72),
    "inputs": {
        "LGE": (0.45, 6.55, 1.25, 0.55),
        "C0 / bSSFP": (0.45, 5.75, 1.25, 0.55),
        "T2": (0.45, 4.95, 1.25, 0.55),
        "mask": (0.28, 3.90, 1.78, 0.72),
    },
    "stems": {
        "LGE stem": (2.20, 6.50, 1.18, 0.62),
        "C0 stem": (2.20, 5.70, 1.18, 0.62),
        "T2 stem": (2.20, 4.90, 1.18, 0.62),
    },
    "encoder": (3.82, 4.65, 1.45, 2.72),
    "router": (5.85, 4.85, 1.70, 1.35),
    "bank": (7.95, 3.98, 2.15, 2.98),
    "alignment": (5.66, 3.35, 3.85, 0.58),
    "decoders": {
        "Anatomy decoder": (10.82, 6.36, 1.56, 0.72),
        "Scar decoder": (10.82, 5.02, 1.56, 0.72),
        "Edema decoder": (10.82, 3.68, 1.56, 0.72),
    },
    "outputs": {
        "ana": (12.85, 6.28, 1.68, 0.88),
        "scar": (12.86, 4.95, 1.15, 0.58),
        "ede": (12.86, 3.61, 1.15, 0.58),
        "prior": (14.10, 5.18, 1.25, 0.72),
        "scar_final": (14.72, 4.76, 0.92, 0.55),
        "ede_final": (14.72, 3.42, 0.92, 0.55),
    },
    "boundary": (0.35, 1.35, 3.80, 1.42),
    "loss": (4.42, 0.92, 5.70, 1.70),
    "cine": (10.62, 0.58, 5.00, 2.34),
}


def center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x, y, w, h = box
    return x + w / 2.0, y + h / 2.0


def side(box: tuple[float, float, float, float], where: str) -> tuple[float, float]:
    x, y, w, h = box
    if where == "left":
        return x, y + h / 2.0
    if where == "right":
        return x + w, y + h / 2.0
    if where == "top":
        return x + w / 2.0, y + h
    if where == "bottom":
        return x + w / 2.0, y
    raise ValueError(where)


def box(
    ax: plt.Axes,
    xywh: tuple[float, float, float, float],
    text: str,
    fc: str,
    ec: str = COLORS["edge"],
    lw: float = 1.0,
    fs: float = 9.2,
    style: str = "round,pad=0.03,rounding_size=0.06",
    dashed: bool = False,
    color: str = "#1F2933",
    ha: str = "center",
) -> FancyBboxPatch:
    x, y, w, h = xywh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=style,
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        linestyle=(0, (4, 3)) if dashed else "solid",
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2.0,
        y + h / 2.0,
        text,
        ha=ha,
        va="center",
        fontsize=fs,
        color=color,
        linespacing=1.15,
    )
    return patch


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = COLORS["edge"],
    lw: float = 1.2,
    dashed: bool = False,
    rad: float = 0.0,
    text: str | None = None,
    text_offset: tuple[float, float] = (0.0, 0.0),
    fs: float = 7.7,
) -> None:
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=10,
        linewidth=lw,
        color=color,
        linestyle=(0, (4, 3)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=4,
        shrinkB=4,
    )
    ax.add_patch(patch)
    if text:
        mx = (start[0] + end[0]) / 2.0 + text_offset[0]
        my = (start[1] + end[1]) / 2.0 + text_offset[1]
        ax.text(mx, my, text, ha="center", va="center", fontsize=fs, color=color)


def draw_encoder(ax: plt.Axes) -> None:
    x, y, w, h = POS["encoder"]
    box(ax, POS["encoder"], "", COLORS["encoder"], fs=9.5)
    ax.text(
        x + w / 2.0,
        y + h - 0.28,
        "multi-scale\nencoder",
        ha="center",
        va="top",
        fontsize=9.0,
        color="#1F2933",
        linespacing=1.05,
    )
    scales = [
        ("l=1   32 ch", y + 1.83),
        ("l=2   64 ch", y + 1.30),
        ("l=3  128 ch", y + 0.77),
        ("l=4  256 ch", y + 0.24),
    ]
    for label, yy in scales:
        box(
            ax,
            (x + 0.18, yy, w - 0.36, 0.36),
            label,
            "#FFFFFF",
            ec="#9AA8B2",
            lw=0.8,
            fs=7.7,
            style="round,pad=0.02,rounding_size=0.03",
        )


def draw_bank(ax: plt.Axes) -> None:
    x, y, w, h = POS["bank"]
    box(
        ax,
        POS["bank"],
        "",
        COLORS["bank"],
        fs=9.6,
    )
    ax.text(
        x + w / 2.0,
        y + h - 0.25,
        "Representation Retrieval\nBank at each scale",
        ha="center",
        va="top",
        fontsize=9.0,
        color="#1F2933",
        linespacing=1.05,
    )
    rows = [
        ("shared dictionary\nD_sh^l", y + 1.98, "#FFFFFF", False),
        ("private dictionaries\nD_LGE^l / D_C0^l / D_T2^l", y + 1.08, "#FFFFFF", False),
        ("optional interaction\nD_mix^l", y + 0.22, COLORS["optional"], True),
    ]
    for label, yy, fc, dashed in rows:
        box(
            ax,
            (x + 0.18, yy, w - 0.36, 0.58),
            label,
            fc,
            ec="#7A5E91",
            lw=0.9,
            fs=7.6,
            dashed=dashed,
            style="round,pad=0.02,rounding_size=0.04",
        )


def draw_cine_inset(ax: plt.Axes) -> None:
    x, y, w, h = POS["cine"]
    box(
        ax,
        POS["cine"],
        "",
        COLORS["cine"],
        ec="#4F8C82",
        lw=1.0,
        fs=8,
        style="round,pad=0.04,rounding_size=0.08",
    )
    ax.text(
        x + 0.18,
        y + h - 0.26,
        "Cine branch: anatomy-first temporal retrieval",
        ha="left",
        va="top",
        fontsize=9.2,
        weight="bold",
        color="#173B36",
    )
    ax.text(
        x + 0.18,
        y + 0.12,
        "same retrieval principle, separate lightweight instance",
        ha="left",
        va="bottom",
        fontsize=7.6,
        color="#315B55",
    )

    small = {
        "frames": (x + 0.28, y + 1.12, 0.92, 0.55),
        "anchor": (x + 1.45, y + 1.04, 1.08, 0.72),
        "dict": (x + 2.78, y + 1.04, 1.16, 0.72),
        "out": (x + 4.16, y + 1.12, 0.62, 0.55),
        "router": (x + 2.78, y + 0.58, 1.16, 0.45),
    }
    box(ax, small["frames"], "cine\nframes", "#FFFFFF", ec="#4F8C82", fs=7.5)
    box(ax, small["anchor"], "ED anchor +\nselected key frames", "#FFFFFF", ec="#4F8C82", fs=7.2)
    box(ax, small["dict"], "temporal\nrepresenter\ndictionary", "#FFFFFF", ec="#4F8C82", fs=6.9)
    box(ax, small["router"], "frame-quality /\nmotion-saliency router", "#FFFFFF", ec="#4F8C82", fs=6.6)
    box(ax, small["out"], "myocardium_\ncinemyops", "#FFFFFF", ec="#4F8C82", fs=6.6)
    arrow(ax, side(small["frames"], "right"), side(small["anchor"], "left"), color="#4F8C82", lw=1.0)
    arrow(ax, side(small["anchor"], "right"), side(small["dict"], "left"), color="#4F8C82", lw=1.0)
    arrow(ax, side(small["router"], "top"), (center(small["dict"])[0], side(small["dict"], "bottom")[1]), color="#4F8C82", lw=0.9)
    arrow(ax, side(small["dict"], "right"), side(small["out"], "left"), color="#4F8C82", lw=1.0)


def draw_figure() -> plt.Figure:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
        }
    )
    fig, ax = plt.subplots(figsize=(16.0, 9.0))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")

    ax.text(
        *POS["title"],
        "Selective Representation Retrieval for Partially Observed Multi-sequence Cardiac MR (SRR-MyoPS)",
        ha="center",
        va="center",
        fontsize=15,
        weight="bold",
        color="#111827",
    )

    # Inputs and masked routing.
    for label, xywh in POS["inputs"].items():
        if label == "mask":
            continue
        box(ax, xywh, label, COLORS["input"], ec="#4D7EA8", fs=9.2)
    box(
        ax,
        POS["inputs"]["mask"],
        "availability mask\nm = (m_LGE, m_C0, m_T2)",
        "#FFFFFF",
        ec="#4D7EA8",
        fs=7.9,
    )
    ax.text(
        0.36,
        3.63,
        "unavailable modality -> masked routing\n(no zero filling as evidence)",
        ha="left",
        va="top",
        fontsize=7.3,
        color=COLORS["muted"],
    )

    for label, xywh in POS["stems"].items():
        box(ax, xywh, "modality-specific\n" + label, COLORS["stem"], ec="#4D7EA8", fs=7.8)

    for input_label, stem_label in zip(
        ["LGE", "C0 / bSSFP", "T2"],
        ["LGE stem", "C0 stem", "T2 stem"],
    ):
        arrow(
            ax,
            side(POS["inputs"][input_label], "right"),
            side(POS["stems"][stem_label], "left"),
            color="#4D7EA8",
            lw=1.0,
        )
        arrow(
            ax,
            side(POS["stems"][stem_label], "right"),
            (POS["encoder"][0], center(POS["stems"][stem_label])[1]),
            color="#4D7EA8",
            lw=1.0,
        )

    draw_encoder(ax)

    # Router and retrieval bank.
    box(
        ax,
        POS["router"],
        "availability + feature router\n\navailability + pooled\nimage features",
        COLORS["router"],
        ec="#B7791F",
        fs=8.0,
    )
    arrow(
        ax,
        side(POS["encoder"], "right"),
        side(POS["router"], "left"),
        color=COLORS["edge"],
        lw=1.2,
        text="multi-scale features",
        text_offset=(0.04, 0.46),
        fs=7.2,
    )
    arrow(
        ax,
        side(POS["inputs"]["mask"], "right"),
        (POS["router"][0] + 0.08, POS["router"][1] + 0.33),
        color="#B7791F",
        lw=1.0,
        rad=0.18,
    )
    draw_bank(ax)

    gate_specs = [
        ("anatomy gate", COLORS["ana"], 5.95, 6.58, 0.12),
        ("scar gate", COLORS["scar"], 5.52, 5.50, 0.00),
        ("edema gate", COLORS["ede"], 5.08, 4.42, -0.12),
    ]
    for label, col, y0, y1, rad in gate_specs:
        arrow(
            ax,
            (side(POS["router"], "right")[0], y0),
            (side(POS["bank"], "left")[0], y1),
            color=col,
            lw=1.25,
            rad=rad,
            text=label,
            text_offset=(0.0, 0.18 if label == "anatomy gate" else -0.16),
            fs=7.2,
        )

    box(
        ax,
        POS["alignment"],
        "optional feature-level LGE-reference alignment expert\ncomplete tri-modal subset only",
        COLORS["optional"],
        ec="#8B8B8B",
        lw=0.9,
        fs=7.2,
        dashed=True,
    )
    arrow(
        ax,
        (side(POS["encoder"], "bottom")[0] + 0.42, side(POS["encoder"], "bottom")[1]),
        side(POS["alignment"], "left"),
        color="#8B8B8B",
        lw=0.9,
        dashed=True,
        rad=-0.08,
    )
    arrow(
        ax,
        side(POS["alignment"], "right"),
        (POS["bank"][0] + POS["bank"][2] * 0.35, side(POS["bank"], "bottom")[1]),
        color="#8B8B8B",
        lw=0.9,
        dashed=True,
        rad=0.10,
    )

    # Decoders and outputs.
    for name, xywh in POS["decoders"].items():
        sub = ""
        if name == "Scar decoder":
            sub = "\nLGE-dominant retrieval"
        elif name == "Edema decoder":
            sub = "\nT2-conditioned retrieval"
        box(ax, xywh, name + sub, COLORS["decoder"], ec="#4B8B4B", fs=7.8)

    route_to_decoder = [
        ("Anatomy decoder", COLORS["ana"], 6.44),
        ("Scar decoder", COLORS["scar"], 5.24),
        ("Edema decoder", COLORS["ede"], 4.06),
    ]
    for name, col, yy in route_to_decoder:
        arrow(ax, (side(POS["bank"], "right")[0], yy), side(POS["decoders"][name], "left"), color=col, lw=1.25)

    box(
        ax,
        POS["outputs"]["ana"],
        "P_union, P_LV, P_RV\nP_union = soft anatomy prior",
        "#FFFFFF",
        ec="#4B8B4B",
        fs=7.5,
    )
    box(ax, POS["outputs"]["scar"], "P_scar", "#FFFFFF", ec=COLORS["scar"], fs=8.3)
    box(ax, POS["outputs"]["ede"], "P_ede", "#FFFFFF", ec=COLORS["ede"], fs=8.3)
    box(
        ax,
        POS["outputs"]["prior"],
        "anatomy\nprior gate\nsoft containment,\nnot hard clipping",
        COLORS["prior"],
        ec="#C05621",
        fs=6.7,
    )
    box(ax, POS["outputs"]["scar_final"], "P_hat_scar", "#FFFFFF", ec=COLORS["scar"], fs=7.2)
    box(ax, POS["outputs"]["ede_final"], "P_hat_ede", "#FFFFFF", ec=COLORS["ede"], fs=7.2)

    arrow(ax, side(POS["decoders"]["Anatomy decoder"], "right"), side(POS["outputs"]["ana"], "left"), color=COLORS["ana"], lw=1.0)
    arrow(ax, side(POS["decoders"]["Scar decoder"], "right"), side(POS["outputs"]["scar"], "left"), color=COLORS["scar"], lw=1.0)
    arrow(ax, side(POS["decoders"]["Edema decoder"], "right"), side(POS["outputs"]["ede"], "left"), color=COLORS["ede"], lw=1.0)
    arrow(ax, side(POS["outputs"]["ana"], "bottom"), side(POS["outputs"]["prior"], "top"), color="#C05621", lw=1.0, rad=-0.08)
    arrow(ax, side(POS["outputs"]["scar"], "right"), side(POS["outputs"]["scar_final"], "left"), color=COLORS["scar"], lw=1.0)
    arrow(ax, side(POS["outputs"]["ede"], "right"), side(POS["outputs"]["ede_final"], "left"), color=COLORS["ede"], lw=1.0)
    arrow(ax, side(POS["outputs"]["prior"], "right"), (side(POS["outputs"]["scar_final"], "left")[0], side(POS["outputs"]["scar_final"], "left")[1] + 0.10), color="#C05621", lw=0.9, rad=0.22)
    arrow(ax, side(POS["outputs"]["prior"], "right"), (side(POS["outputs"]["ede_final"], "left")[0], side(POS["outputs"]["ede_final"], "left")[1] - 0.06), color="#C05621", lw=0.9, rad=-0.18)

    ax.text(
        POS["outputs"]["scar"][0] + 0.52,
        POS["outputs"]["scar"][1] - 0.28,
        "component-aware inference\nfor remote FP / HD95",
        ha="center",
        va="top",
        fontsize=6.9,
        color=COLORS["scar"],
    )
    ax.text(
        POS["outputs"]["ede"][0] + 0.58,
        POS["outputs"]["ede"][1] - 0.28,
        "T2-masked edema loss:\nno-T2 is not negative",
        ha="center",
        va="top",
        fontsize=6.9,
        color=COLORS["ede"],
    )

    box(
        ax,
        POS["loss"],
        "Training objectives\n\nL_total = L_ana + L_scar + m_T2 L_ede + L_sparse + L_sip\n+ L_lb + L_prior (+ L_align optional)\n\nR2/BR2-inspired segmentation-native retrieval:\ndictionary/gates are dense feature modules,\nnot the original linear learner or discrete SIP copied into 3D segmentation.",
        COLORS["loss"],
        ec="#8B7355",
        fs=7.0,
    )
    arrow(ax, (12.95, 4.72), (9.95, 2.45), color="#8B7355", lw=0.8, dashed=True, rad=0.18)
    arrow(ax, (13.02, 3.43), (9.75, 1.78), color="#8B7355", lw=0.8, dashed=True, rad=0.18)

    box(
        ax,
        POS["boundary"],
        "Core boundary\n\nMyoPS main line: availability-aware,\npathology-specific retrieval.\n\nMissing modalities are masked; no-T2 cases\nare not edema negatives.",
        "#FFFFFF",
        ec="#9AA8B2",
        fs=7.3,
    )

    draw_cine_inset(ax)

    return fig


def write_caption() -> Path:
    caption = """# SRR-MyoPS Architecture Caption

**Figure. Selective Representation Retrieval for Partially Observed Multi-sequence Cardiac MR (SRR-MyoPS).** SRR-MyoPS uses modality-specific stems for LGE, C0/bSSFP, and T2, followed by a multi-scale encoder whose features are routed through shared and modality-private representation dictionaries. The router is conditioned on both the modality availability mask and pooled image features, producing anatomy-, scar-, and edema-specific retrieval gates rather than treating missing modalities as zero-filled evidence. Pathology-specific decoders use LGE-dominant retrieval for scar and T2-conditioned retrieval for edema, while the anatomy decoder produces a soft union prior that gates pathology predictions by soft containment rather than hard clipping. Edema supervision is T2-masked, so no-T2 cases are not treated as edema-negative examples. The optional alignment expert is restricted to feature-level LGE-reference alignment on complete tri-modal cases. The Cine branch is shown as a separate lightweight anatomy-first temporal retrieval instance that applies the same retrieval principle to ED anchors, selected key frames, and motion-saliency cues; it is not a single large unified 4D-plus-multisequence model. The design is a segmentation-native adaptation inspired by R2/BR2-style representation retrieval, not a direct claim that the original linear learner or SIP theory directly covers dense CMR segmentation.
"""
    path = BASE.with_name(BASE.name + "_caption.md")
    path.write_text(caption, encoding="utf-8")
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = draw_figure()
    outputs = [
        BASE.with_suffix(".svg"),
        BASE.with_suffix(".pdf"),
        BASE.with_suffix(".png"),
    ]
    for path in outputs:
        if path.suffix == ".png":
            fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
        else:
            fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    outputs.append(write_caption())
    for path in outputs:
        print(f"{path} {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
