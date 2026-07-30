#!/usr/bin/env python3
"""Render the V3 CARE forensics packet with Pandoc + XeLaTeX.

The source text is generated from V3 machine-readable state files.  This script
does not use Chromium fallback and does not promote NEEDS_REPAIR to complete.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


CARE_ROOT = Path("/users/a/e/aereinh/CARE")
RESOURCE_DIR = Path("/users/a/e/aereinh/render_resources/chinese_math_pdf")
PYTHON = CARE_ROOT / "envs/env_CARE/bin/python"
OUT_DIR = CARE_ROOT / "results/20260730_care_failure_forensics_deep_research_packet"
PDF_NAME = "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v3.pdf"


def run(cmd: list[str], cwd: Path = CARE_ROOT, timeout: int = 240, env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows if limit is None else rows[:limit]


def md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def latex(value: object) -> str:
    text = str(value)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def pagebreak() -> str:
    return "\n\\newpage\n"


def short(value: object, width: int = 42) -> str:
    text = md(value)
    if "/" in text:
        parts = [p for p in text.split("/") if p]
        if len(parts) > 3:
            text = f"{parts[0]}/.../{parts[-1]}"
    if len(text) > width:
        return text[: width - 3] + "..."
    return text


def table(rows: list[dict[str, str]], fields: list[str], widths: dict[str, int] | None = None) -> str:
    if not rows:
        return "_无记录。_"
    widths = widths or {}
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(short(row.get(f, ""), widths.get(f, 34)) for f in fields) + " |")
    return "\n".join(lines)


def counts(rows: list[dict[str, str]], key: str) -> list[dict[str, str]]:
    out: dict[str, int] = {}
    for row in rows:
        out[row.get(key, "")] = out.get(row.get(key, ""), 0) + 1
    return [{key: k or "EMPTY", "rows": str(v)} for k, v in sorted(out.items())]


def png(path: Path, alt: str, width: str = "0.95\\linewidth") -> str:
    return rf"\begin{{center}}\includegraphics[width={width}]{{\detokenize{{{path.resolve()}}}}}\end{{center}}"


def atlas_png(path: Path) -> str:
    return (
        r"\begin{center}"
        + rf"\includegraphics[width=0.98\linewidth,height=0.91\textheight,keepaspectratio]{{\detokenize{{{path.resolve()}}}}}"
        + r"\end{center}"
    )


def write_source(out: Path) -> Path:
    source_dir = out / "report_source_v3"
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / "CARE_failure_forensics_20260730_v3.md"

    final_state = read_json(out / "v3_final_task_state.json")
    data_truth = read_json(out / "v3_t2_availability_audit.json")
    feature_receipt = read_json(out / "v3_feature_probe_receipt.json")
    mosaic_receipt = read_json(out / "v3_mosaic_activation_probe_receipt.json")
    evidence_state = read_csv(out / "v3_final_evidence_state.csv")
    missing = read_csv(out / "v3_missing_scientific_evidence.csv")
    feature_summary = read_csv(out / "v3_feature_probe_summary.csv")
    atlas_manifest = read_csv(out / "v3_case_atlas_manifest.csv")
    atlas_quality = read_csv(out / "v3_case_atlas_quality.csv")
    lineage = read_csv(out / "v3_batch0_7_lineage.csv")
    mosaic_summary = read_csv(out / "v3_mosaic_m0_m10_summary.csv")
    large_gain = read_csv(out / "v3_large_gain_upper_bound.csv")
    claim_rows = read_csv(out / "v3_v2_contradiction_audit.csv")

    feature_sources = counts(feature_summary, "feature_source")
    feature_status = counts(feature_summary, "status")
    probe_status = counts(feature_summary, "probe_model")
    mosaic_train_n = len(mosaic_receipt.get("train_cases", []))
    mosaic_eval_n = len(mosaic_receipt.get("eval_cases", []))
    remaining_blockers = "; ".join(row.get("notes", "") for row in final_state.get("current_blockers", [])) or "none"

    lines: list[str] = [
        "---",
        "title: CARE Failure Forensics Deep Research Evidence Packet V3",
        "author: CARE Forensic Evidence Finalization Controller",
        "date: 20260730 V3 machine-state render",
        "---",
        "",
        "# 封面",
        "",
        "这份 PDF 是 CARE Myocardium 失败取证 V3 的 XeLaTeX/Pandoc 渲染稿，使用 `/users/a/e/aereinh/render_resources/chinese_math_pdf` 中的 xeCJK/ctex 与 Noto CJK 字体资源。它不是 Chromium/Skia 输出，不包含 validation upload，不包含 Docker upload，不启动新架构训练。",
        "",
        f"当前 controller 判定：`{final_state.get('controller_verification_decision', 'UNKNOWN')}`。",
        "",
        "如果本文显示 `NEEDS_REPAIR`，它表示机器证据仍未满足终态 strict validator；不得把本稿当作已完成科学结论。",
        "",
        pagebreak(),
        "# 执行摘要",
        "",
        f"当前 V3 已修正 V2 的关键数据错误：T2-present 不是 220，而是 `{data_truth.get('t2_present', 'UNKNOWN')}` 个 raw/meta 真实可用病例。scar 固定为 label 5；official pure edema 固定为真实 T2-present 病例中的 label 4；edema-zone 只作为内部结构指标，不替代 official edema。",
        "",
        f"feature probe 方面，nnU-Net encoder/decoder、PRISM shared/private/routed/refiner、RAW_INTENSITY_CONTROL 以及 MoSAIC coarse/scar-fine/edema 均已进入合并 summary。MoSAIC hook 已对齐 feature probe split：actual_train={mosaic_train_n}、inner_select={mosaic_eval_n}，outer split 未访问。controller 当前仍保留 `NEEDS_REPAIR` 的原因是：{remaining_blockers}。",
        "",
        "# 关键机器状态",
        "",
        table(evidence_state, ["task_id", "status", "terminal_status", "evidence_path", "notes"], {"notes": 70}),
        "",
        "# 当前剩余资产边界",
        "",
        table(missing, ["asset_or_evidence", "status", "why_it_matters", "next_action"], {"why_it_matters": 72, "next_action": 72}),
        "",
        pagebreak(),
        "# 1. 数据和 T2 availability 真值",
        "",
        "V3 不再从 nnU-Net 三通道 slot 推断 T2/C0 是否可用。真实 availability 由 raw dataset、metadata、subject_meta、dataset.json 描述和文件名共同冻结。",
        "",
        table([
            {"field": "case_count", "value": data_truth.get("case_count", "")},
            {"field": "t2_present", "value": data_truth.get("t2_present", "")},
            {"field": "t2_absent", "value": data_truth.get("t2_absent", "")},
            {"field": "c0_present", "value": data_truth.get("c0_present", "")},
            {"field": "scar_positive_label5", "value": data_truth.get("scar_positive_label5", "")},
            {"field": "pure_edema_positive_official_t2_present", "value": data_truth.get("pure_edema_positive_official_t2_present", "")},
        ], ["field", "value"]),
        "",
        table(read_csv(out / "v3_canonical_modality_manifest.csv", 14), ["case_id", "center", "canonical_modalities", "T2_present", "C0_present"], {"canonical_modalities": 24}),
        "",
        pagebreak(),
        "# 2. 标签可靠性",
        "",
        "scar、pure edema 和 edema-zone 在 V3 中分开声明。no-T2 病例不得作为 official pure-edema 阴性监督；edema-zone 只能用于内部结构分析。",
        "",
        table(read_csv(out / "v3_label_reliability_manifest.csv", 18), ["case_id", "center", "scar_label_reliable", "pure_edema_label_reliable", "edema_zone_internal_valid"], {}),
        "",
        pagebreak(),
        "# 3. V2 矛盾修复摘要",
        "",
        table(claim_rows, ["contradiction_id", "v2_statement_a", "v2_statement_b", "v3_truth_source", "resolution"], {"v2_statement_a": 60, "v2_statement_b": 60, "resolution": 64}),
        "",
        "# 4. Batch0-7 与 Batch7",
        "",
        "V3 的 Batch0-7 表不能仅由当前 main 文件存在与否判断。当前表保留 checkpoint/prediction/metric binding 等证据等级，缺 exact replay 的项目不写成负结果。",
        "",
        table(lineage, ["batch_id", "commit", "design_goal", "checkpoint", "prediction", "evidence_grade", "reusable_experience"], {"design_goal": 60, "reusable_experience": 70}),
        "",
        pagebreak(),
        "# 5. MMRD",
        "",
        "MMRD 仍是 V3 的高风险缺口之一：checkpoint binding 与 decoder inheritance audit 已有记录，但 casewise metrics/direct-distillation comparison 仍不足以支撑终态结论。后续 validator 必须拒绝“有 checkpoint 但未尝试 load/replay”的假完成。",
        "",
        table(read_csv(out / "v3_mmrd_component_effect.csv", 12), ["component", "implemented", "checkpoint_bound", "prediction_bound", "future_status", "failure_reason"], {"failure_reason": 70}),
        "",
        "# 6. Cascade",
        "",
        table(read_csv(out / "v3_cascade_component_effect.csv", 12), ["component", "implemented", "entered_final_logits", "casewise_effect", "future_status", "failure_reason"], {"failure_reason": 70}),
        "",
        pagebreak(),
        "# 7. ARC",
        "",
        table(read_csv(out / "v3_arc_component_effect.csv", 12), ["component", "implemented", "entered_final_logits", "casewise_effect", "future_status", "failure_reason"], {"failure_reason": 70}),
        "",
        "# 8. MoSAIC code/weights 与 M0-M10",
        "",
        "MoSAIC 被分成 clean OOF、full-data diagnostic 和 hosted-near recipe。full-data 或 hosted-near 结果不得写成 clean architecture superiority。",
        "",
        table(mosaic_summary, ["stage_id", "stage_name", "checkpoint_scope", "case_count", "mean_scar_dice", "mean_pure_edema_dice", "runtime"], {"stage_name": 54}),
        "",
        pagebreak(),
        "# 9. Frozen Feature Probes",
        "",
        f"主 receipt：`{feature_receipt.get('status', 'UNKNOWN')}`。MoSAIC hook receipt：`{mosaic_receipt.get('status', 'UNKNOWN')}`。outer split 未访问：`{feature_receipt.get('outer_accessed', '')}`。",
        "",
        "feature source 覆盖：",
        "",
        table(feature_sources, ["feature_source", "rows"], {"feature_source": 46}),
        "",
        "probe 模型覆盖：",
        "",
        table(probe_status, ["probe_model", "rows"]),
        "",
        "probe 状态分布：",
        "",
        table(feature_status, ["status", "rows"]),
        "",
        pagebreak(),
        "# 10. scar evidence brief",
        "",
        (out / "v3_scar_evidence_brief.md").read_text(encoding="utf-8") if (out / "v3_scar_evidence_brief.md").exists() else "_missing_",
        "",
        pagebreak(),
        "# 11. pure-edema evidence brief",
        "",
        (out / "v3_pure_edema_evidence_brief.md").read_text(encoding="utf-8") if (out / "v3_pure_edema_evidence_brief.md").exists() else "_missing_",
        "",
        pagebreak(),
        "# 12. 0.1 Dice large-gain feasibility",
        "",
        "V3 不允许把 voxel oracle 写成可部署性能。若 simple nnU-Net/MoSAIC case oracle 只有小幅增益，则必须说明 0.1 级增益缺少何种新机制证据。",
        "",
        table(large_gain, ["metric_name", "case_oracle_gain", "feature_probe_based_bound", "recipe_only_bound", "single_backbone_new_mechanism_plausible_bound", "conclusion"], {"conclusion": 64}),
        "",
        (out / "v3_large_gain_feasibility.md").read_text(encoding="utf-8") if (out / "v3_large_gain_feasibility.md").exists() else "",
        "",
        pagebreak(),
        "# 13. Cine 和 alignment",
        "",
        (out / "v3_cine_alignment_conclusion.md").read_text(encoding="utf-8") if (out / "v3_cine_alignment_conclusion.md").exists() else "",
        "",
        table(read_csv(out / "v3_alignment_failure_correlation.csv", 12), ["case_id", "center", "lge_t2_centroid_shift_vox", "lge_c0_centroid_shift_vox", "failure_correlation"], {"failure_correlation": 60}),
        "",
        pagebreak(),
        "# 14. Deep Research 约束输入",
        "",
        "完整 Deep Research 输入文件单独保存为 `DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730.md`。PDF 这里只呈现核心边界：不能复制失败实现；不能让 nnU-Net/MoSAIC 成为唯一主体；scar 与 pure edema 必须同等建模；不能接受只有 0.005-0.02 Dice 的 recipe 小修；0.1 级增益必须由 error budget 和 feature evidence 共同约束。",
        "",
        pagebreak(),
        "# 15. 40 例视觉图册总览",
        "",
        "每个病例单独使用 landscape 页面，避免 V2 的横向 panel 裁切。图册 QA 表显示 40 个病例、0 个 QA fail；MoSAIC full/final panel 若未绑定原始 mask，会在图中明确显示 `not bound`，不得用 aggregate CSV 合成。",
        "",
        table(atlas_quality, ["case_id", "status", "width", "height", "qa_notes"], {"qa_notes": 70}),
        "",
    ]

    contact = out / "case_montages_v3/contact_sheet_40_cases.png"
    if contact.exists():
        lines += [png(contact, "40 case contact sheet", "0.98\\linewidth"), ""]

    for idx, row in enumerate(atlas_manifest, 1):
        atlas_value = str(row.get("atlas_path") or row.get("montage_path") or "")
        image_path = CARE_ROOT / atlas_value if atlas_value.startswith("results/") else out / atlas_value
        if not image_path.exists():
            continue
        case_id = row.get("case_id", f"case_{idx}")
        lines += [
            pagebreak(),
            r"\begin{landscape}",
            "",
            r"\thispagestyle{plain}",
            r"\vspace*{-8mm}",
            atlas_png(image_path),
            "",
            r"\end{landscape}",
            "",
        ]

    appendix_specs = [
        ("附录 A：feature summary 分块", "v3_feature_probe_summary.csv", ["feature_source", "task_id", "probe_model", "status", "AUROC", "AUPRC", "balanced_accuracy"], 120),
        ("附录 B：MoSAIC M0-M10 casewise 分块", "v3_mosaic_m0_m10_casewise.csv", ["case_id", "stage_id", "scar_dice", "pure_edema_dice", "edema_zone_dice", "changed_voxels"], 80),
        ("附录 C：Batch0-7 casewise 分块", "v3_batch0_7_casewise_metrics.csv", ["case_id", "batch_id", "scar_result", "pure_edema_result", "edema_zone_result", "help", "harm"], 80),
        ("附录 D：claim/search contradiction ledger", "v3_v2_stale_statement_audit.csv", ["file", "line", "pattern", "classification", "v3_action"], 80),
    ]
    for title, filename, fields, limit in appendix_specs:
        rows = read_csv(out / filename, limit)
        for start in range(0, len(rows), 12):
            lines += [pagebreak(), f"# {title} {start // 12 + 1}", "", table(rows[start : start + 12], fields, {f: 48 for f in fields}), ""]

    source.write_text("\n".join(str(x) for x in lines), encoding="utf-8")
    return source


def render_pdf(source: Path, out: Path) -> None:
    header = Path("/tmp/chinese-math-header.tex")
    code, header_out = run([str(PYTHON), "scripts/build_chinese_math_header.py", "--root", str(CARE_ROOT), "--output", str(header)])
    if code != 0:
        raise SystemExit(header_out)
    cache = Path("/tmp/care_forensics_v3_xelatex_cache")
    for sub in ["var", "config", "cache"]:
        (cache / sub).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "TEXINPUTS": f"{RESOURCE_DIR}/texmf//:",
            "TEXMFVAR": str(cache / "var"),
            "TEXMFCONFIG": str(cache / "config"),
            "TEXMFCACHE": str(cache / "cache"),
        }
    )
    pdf = out / PDF_NAME
    cmd = [
        "pandoc",
        str(source),
        "--from",
        "markdown+tex_math_dollars+tex_math_single_backslash+raw_tex+link_attributes",
        "--pdf-engine=xelatex",
        "--include-in-header",
        str(header),
        "-V",
        "papersize:a4",
        "-V",
        "geometry:margin=16mm",
        "-V",
        "fontsize=10.5pt",
        "-o",
        str(pdf),
    ]
    code, log = run(cmd, timeout=600, env=env)
    (out / "report_source_v3/xelatex_render.log").write_text(log, encoding="utf-8", errors="ignore")
    (out / "report_source_v3/build_commands.txt").write_text(
        "TEXINPUTS=/users/a/e/aereinh/render_resources/chinese_math_pdf/texmf//: "
        "TEXMFVAR=/tmp/care_forensics_v3_xelatex_cache/var "
        "TEXMFCONFIG=/tmp/care_forensics_v3_xelatex_cache/config "
        "TEXMFCACHE=/tmp/care_forensics_v3_xelatex_cache/cache "
        + " ".join(cmd)
        + "\n",
        encoding="utf-8",
    )
    if code != 0:
        raise SystemExit(log)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def qa_pdf(out: Path) -> None:
    pdf = out / PDF_NAME
    code, info = run(["pdfinfo", str(pdf)])
    (out / "v3_pdfinfo.txt").write_text(info, encoding="utf-8", errors="ignore")
    code, fonts = run(["pdffonts", str(pdf)])
    (out / "v3_pdffonts.txt").write_text(fonts, encoding="utf-8", errors="ignore")
    run(["pdftotext", "-layout", str(pdf), str(out / "v3_pdf_text_extract.txt")], timeout=240)
    pages = out / "v3_pdf_pages"
    if pages.exists():
        shutil.rmtree(pages)
    pages.mkdir()
    run(["pdftoppm", "-png", "-r", "150", str(pdf), str(pages / "page")], timeout=600)
    page_rows = []
    for idx, png_path in enumerate(sorted(pages.glob("page-*.png")), 1):
        im = Image.open(png_path).convert("L")
        arr = np.asarray(im)
        page_rows.append(
            {
                "page": idx,
                "path": str(png_path.relative_to(out)),
                "width": im.width,
                "height": im.height,
                "pixel_std": float(arr.std()),
                "status": "PASS_NONBLANK" if float(arr.std()) > 1.0 else "FAIL_BLANK",
            }
        )
    with (out / "v3_pdf_page_quality.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["page", "path", "width", "height", "pixel_std", "status"]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(page_rows)
    first_pages = sorted(pages.glob("page-*.png"))[:24]
    if first_pages:
        sheet = Image.new("RGB", (4 * 260, 6 * 350), "white")
        draw = ImageDraw.Draw(sheet)
        for i, page in enumerate(first_pages):
            im = Image.open(page).convert("RGB")
            im.thumbnail((240, 315))
            x = (i % 4) * 260
            y = (i // 4) * 350
            draw.text((x + 4, y + 2), page.name, fill="black")
            sheet.paste(im, (x, y + 24))
        sheet.save(out / "v3_pdf_contact_sheet.png")
    report = {
        "pdf": str(pdf),
        "exists": pdf.exists(),
        "size_bytes": pdf.stat().st_size if pdf.exists() else 0,
        "sha256": sha256(pdf) if pdf.exists() else "",
        "route": "pandoc_xelatex_named_fonts",
        "render_resource_dir": str(RESOURCE_DIR),
        "chromium_fallback_used": False,
        "page_count_from_png": len(page_rows),
        "page_quality_failures": [r for r in page_rows if not r["status"].startswith("PASS")],
        "pdfinfo_path": "v3_pdfinfo.txt",
        "pdffonts_path": "v3_pdffonts.txt",
        "pdftotext_path": "v3_pdf_text_extract.txt",
        "contact_sheet": "v3_pdf_contact_sheet.png",
    }
    (out / "v3_pdf_validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    out = args.root.resolve()
    source = write_source(out)
    render_pdf(source, out)
    qa_pdf(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
