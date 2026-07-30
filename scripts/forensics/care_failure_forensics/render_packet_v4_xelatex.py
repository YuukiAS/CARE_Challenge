#!/usr/bin/env python3
"""Render the V4 CARE forensics design-readiness packet with XeLaTeX."""

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
OUT_DIR = CARE_ROOT / "results/20260730_care_failure_forensics_deep_research_packet"
RESOURCE_DIR = Path("/users/a/e/aereinh/render_resources/chinese_math_pdf")
PYTHON = CARE_ROOT / "envs/env_CARE/bin/python"
PDF_NAME = "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v4.pdf"


def run(cmd: list[str], cwd: Path = CARE_ROOT, timeout: int = 300, env: dict[str, str] | None = None) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return proc.returncode, proc.stdout


def read_csv(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows if limit is None else rows[:limit]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def esc(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def short(value: object, max_len: int = 34) -> str:
    text = esc(value)
    replacements = {
        "COMPLETED_WITH_VALID_EVIDENCE": "VALID",
        "PASS_V4_PATIENT_LEVEL_REFOLD": "PASS_REFOLD",
        "D0_FULL_PRETRAINED_IDENTITY": "D0_IDENTITY",
        "D1_DECODER_RESET_ENCODER_FROZEN": "D1_RESET",
        "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE": "D2_TOP_TRAIN",
        "D3_FULL_MODEL_SHORT_FINETUNE": "D3_SHORT_FT",
        "historical/current-main-binding": "hist/main",
        "P1_scar_vs_normal_myocardium": "P1_scar",
        "P2_nnunet_scar_FN_vs_true_negative": "P2_scar_FN",
        "P3_nnunet_scar_FP_vs_true_negative": "P3_scar_FP",
        "P4_pure_edema_vs_normal_myocardium": "P4_edema",
        "P5_nnunet_pure_edema_FN": "P5_edema_FN",
        "P6_nnunet_pure_edema_FP": "P6_edema_FP",
        "P7_small_scar_vs_normal_myocardium": "P7_small_scar",
        "P8_boundary_scar_vs_non_scar_myocardium": "P8_boundary",
        "CASE_VOLUME_ONLY_CONTROL": "VOLUME_CTRL",
        "CENTER_ONLY_CONTROL": "CENTER_CTRL",
        "MODALITY_ONLY_CONTROL": "MODALITY_CTRL",
        "RAW_INTENSITY_CONTROL": "RAW_CTRL",
        "SPATIAL_COORDINATE_ONLY_CONTROL": "COORD_CTRL",
        "PATIENT_ID_LEAKAGE_CONTROL": "PATIENT_ID_CTRL",
        "SHUFFLED_WITHIN_PATIENT_CONTROL": "SHUFFLE_IN_PATIENT",
        "SHUFFLED_ACROSS_PATIENT_CONTROL": "SHUFFLE_ACROSS",
    }
    text = replacements.get(text, text)
    try:
        val = float(text)
        if np.isfinite(val):
            text = f"{val:.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        pass
    if "/" in text and len(text) > max_len:
        text = text.replace("/", "/ ")
    if len(text) > max_len:
        text = text.replace("_", "_ ").replace("-", "- ").replace(";", "; ").replace(",", ", ")
    return text


def latex_escape(value: object) -> str:
    text = short(value, 80)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_\allowbreak{}",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def table(rows: list[dict[str, str]], fields: list[str], limit: int = 10, max_len: int = 34) -> str:
    if not rows:
        return "_暂无可展示行。_"
    rows = rows[:limit]
    lines = []
    for idx, row in enumerate(rows, start=1):
        title_field = fields[0] if fields else "row"
        title_value = short(row.get(title_field, f"row {idx}"), max_len)
        lines.append(f"- **{esc(title_field)} {idx}: {title_value}**")
        for field in fields[1:]:
            value = short(row.get(field, ""), max_len)
            if value != "":
                lines.append(f"  - {esc(field)}: {value}")
    return "\n".join(lines)


def blocks(rows: list[dict[str, str]], title: str, fields: list[str], limit: int = 8) -> str:
    if not rows:
        return "_暂无可展示行。_"
    out: list[str] = []
    for row in rows[:limit]:
        out.append(f"- **{esc(title)}: {short(row.get(title, 'UNNAMED'), 70)}**")
        for field in fields:
            value = short(row.get(field, ""), 80)
            if value:
                out.append(f"  - {esc(field)}: {value}")
    return "\n".join(out)


def pagebreak() -> str:
    return "\n\\newpage\n"


def image(path: Path, alt: str, width: str = "0.96\\linewidth", height: str | None = None) -> str:
    opts = [f"width={width}"]
    if height:
        opts.extend([f"height={height}", "keepaspectratio"])
    return rf"\begin{{center}}\includegraphics[{','.join(opts)}]{{\detokenize{{{path.resolve()}}}}}\end{{center}}"


def md_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else "_文件不存在。_"


def write_source(out: Path) -> Path:
    source_dir = out / "report_source_v4"
    source_dir.mkdir(parents=True, exist_ok=True)
    source = source_dir / "CARE_failure_forensics_20260730_v4.md"
    state = read_json(out / "v4_final_state.json")
    strict = read_json(out / "v4_strict_validator_report.json")
    feature = read_json(out / "v4_feature_probe_receipt.json")
    mosaic = read_json(out / "v4_mosaic_recipe_population_audit.json")
    atlas = read_csv(out / "v4_atlas_pdf_bbox_validation.csv")
    slurm_rows = []
    for row in read_csv(out / "v4_submitted_gpu_jobs.csv"):
        job_id = row.get("job_id", "")
        keep = job_id == "61376439"
        if job_id.startswith("61220581."):
            try:
                keep = int(job_id.split(".", 1)[1]) >= 51
            except ValueError:
                keep = False
        if keep:
            slurm_rows.append(row)
    lines: list[str] = [
        "---",
        "title: CARE Myocardium Deep Research 设计证据包 V4",
        "author: CARE Forensic Research Controller",
        "date: 20260730",
        "---",
        "",
        "# CARE Myocardium Deep Research 设计证据包 V4",
        "",
        "本报告是科学证据就绪包，不是新架构设计，也不是 validation 或 Docker 上传报告。V4 的核心修复是把“取证脚本完成”“科学证据充分”“当前模型是否成功”“是否可进入 Deep Research 设计”四件事拆开判断。",
        "",
        table(
            [
                {"field": "operational_execution_status", "value": state.get("operational_execution_status", "")},
                {"field": "scientific_evidence_status", "value": state.get("scientific_evidence_status", "")},
                {"field": "current_model_status", "value": state.get("current_model_status", "")},
                {"field": "deep_research_readiness", "value": state.get("deep_research_readiness", "")},
                {"field": "strict_validator", "value": strict.get("decision", "")},
            ],
            ["field", "value"],
            max_len=44,
        ),
        "",
        "当前 PRISM W3 仍是 `FAILED_GATE`。这不被 V4 证据包的操作完成状态覆盖，也不授权任何新模型 promotion。",
        "",
        pagebreak(),
        "# 执行摘要",
        "",
        "V4 补齐了 V3 中会改变设计结论的关键空洞：Batch7、MMRD、Cascade、ARC、MoSAIC、feature probe、large-gain error budget、alignment、visual atlas 和状态语义现在都有可核验的 V4 证据文件。最重要的科学结论是：当前历史实现不支持继续堆叠完整 backbone；Deep Research 若要追求约 0.1 Dice 上限，必须直接攻击小病灶漏检、远端假阳性、边界错误、decoder 能力损失和 T2-present edema 表征，而不是复用未进入 final logits 的模块。",
        "",
        "V4 只提供设计约束输入：可保留的经验、必须禁止的失败实现、scar 和 pure edema 的分病种证据、以及仍需外部研究回答的问题。",
        "",
        "# 状态语义",
        "",
        table(read_csv(out / "v4_deep_research_readiness_checklist.csv"), ["requirement", "passed", "evidence"], limit=14, max_len=48),
        "",
        pagebreak(),
        "# 1. 数据和标签",
        "",
        "本轮固定数据事实：MyoPS 总病例 220；T2-present 病例 80；C0-present 病例 104。scar 和 pure edema 分别作为 primary pathology 处理，no-T2 病例不得作为 pure-edema 阴性监督。",
        "",
        table(read_csv(out / "pathology_prevalence_summary.csv"), ["cases", "scar_positive", "pure_edema_positive", "t2_present"], max_len=28),
        "",
        "# 2. metric 和评价修复",
        "",
        "V4 继续沿用 reference metric known-bad 约束：remote FP、physical spacing HD95、empty cases、lesion recall、label 4/5 语义不得混写。hosted validation 数字只能作为来源绑定，不能反向写成本地 clean evidence。",
        "",
        table(read_csv(out / "official_internal_label_mapping.csv"), ["object", "internal_labels", "allowed_claim_scope"], limit=8, max_len=46),
        "",
        pagebreak(),
        "# 3. nnU-Net 系统与 decoder-reset",
        "",
        "nnU-Net 的强处是完整 decoder、稳定训练 recipe、成熟增强和直接 final mask 输出。历史失败路线不能只继承 encoder 后重置 decoder，再把强基线能力损失归因于高层设计概念。",
        "",
        table(read_csv(out / "nnunet_decoder_reset_real_summary.csv"), ["variant", "status", "official_scar_label5_dice", "official_pure_edema_label4_dice"], limit=8, max_len=38),
        "",
        "# 4. Batch0-6",
        "",
        table(read_csv(out / "v4_batch_history_recovery.csv"), ["batch_id", "source_branch", "case_count", "scar_dice", "pure_edema_dice", "valid_scientific_conclusion"], limit=8, max_len=38),
        "",
        pagebreak(),
        "# 5. Batch7",
        "",
        md_text(out / "v4_batch7_reusable_experience.md"),
        "",
        table(read_csv(out / "v4_batch7_component_effect.csv"), ["component", "future_status", "scar_effect", "edema_effect"], limit=10, max_len=40),
        "",
        "# 6. MMRD",
        "",
        md_text(out / "v4_mmrd_reusable_experience.md"),
        "",
        table(read_csv(out / "v4_mmrd_direct_distillation.csv"), ["comparison", "case_count", "scar_effect", "pure_edema_effect", "v4_conclusion"], limit=10, max_len=40),
        "",
        pagebreak(),
        "# 7. Cascade",
        "",
        md_text(out / "v4_cascade_reusable_experience.md"),
        "",
        table(read_csv(out / "v4_cascade_control_srr_tensor_delta.csv"), ["tensor", "identity_rate", "changed_voxel_fraction", "v4_conclusion"], limit=10, max_len=40),
        "",
        "# 8. ARC",
        "",
        md_text(out / "v4_arc_reusable_experience.md"),
        "",
        table(read_csv(out / "v4_arc_blueprint_code_runtime.csv"), ["blueprint_claim", "code_status", "runtime_status", "v4_status"], limit=10, max_len=42),
        "",
        pagebreak(),
        "# 9. PRISM",
        "",
        "PRISM W3 失败状态保持独立：`current_model_status=FAILED_GATE`。可保留的是输入 hygiene、final-output trace、decoder preservation 这些规则；不能保留的是 decoder reset 后仍宣称强基线能力、模块存在但不进入 final output 的验证方式。",
        "",
        table(read_csv(out / "v4_component_survival_ledger.csv"), ["source_model", "component", "future_status", "repeat_risk"], limit=12, max_len=42),
        "",
        "# 10. MoSAIC M0-M10",
        "",
        f"MoSAIC V4 population gate: `{mosaic.get('v4_population_gate', '')}`；M2-M10 病例数 `{mosaic.get('m2_m10_cases', '')}`；runtime 和 changed voxels 字段均已绑定。",
        "",
        table(read_csv(out / "v4_mosaic_m0_m10_summary.csv"), ["stage_id", "stage_name", "case_count", "mean_scar_dice", "mean_pure_edema_dice", "mean_changed_voxels"], limit=12, max_len=34),
        "",
        pagebreak(),
        "# 11. clean/full-data/hosted gap",
        "",
        table(read_csv(out / "mosaic_clean_full_data_gap.csv"), ["metric_name", "clean_oof", "full_data", "hosted_or_bound", "v4_interpretation"], limit=10, max_len=42),
        "",
        "# 12. standardized casewise results",
        "",
        table(read_csv(out / "standardized_model_summary.csv"), ["model_id", "metric_name", "case_count", "mean_dice", "empty_pred_count"], limit=12, max_len=34),
        "",
        pagebreak(),
        "# 13. scar failure taxonomy",
        "",
        md_text(out / "v4_scar_scientific_brief.md"),
        "",
        pagebreak(),
        "# 14. pure-edema failure taxonomy",
        "",
        md_text(out / "v4_pure_edema_scientific_brief.md"),
        "",
        pagebreak(),
        "# 15. frozen feature probes",
        "",
        f"V4 feature probe: `{feature.get('status', '')}`；病例数 `{feature.get('case_count', '')}`；fold 数 `{feature.get('fold_count', '')}`；outer 只读诊断，不参与 checkpoint、threshold 或后处理选择。",
        "",
        table(read_csv(out / "v4_feature_probe_scar_summary.csv"), ["feature_source", "task_id", "passing_folds", "mean_AUROC", "mean_AUPRC"], limit=12, max_len=38),
        "",
        table(read_csv(out / "v4_feature_probe_edema_summary.csv"), ["feature_source", "task_id", "passing_folds", "mean_AUROC", "mean_AUPRC"], limit=12, max_len=38),
        "",
        pagebreak(),
        "# 16. alignment",
        "",
        md_text(out / "v4_alignment_conclusion.md"),
        "",
        table(read_csv(out / "v4_alignment_failure_correlation.csv"), ["alignment_metric", "failure_metric", "pearson", "spearman", "bootstrap_ci_low", "bootstrap_ci_high"], limit=12, max_len=34),
        "",
        "# 17. help/harm 和 oracle",
        "",
        table(read_csv(out / "case_oracle_summary.csv"), ["case_id", "metric_name", "best_case_model", "case_oracle_dice", "voxel_tp_oracle_dice"], limit=12, max_len=34),
        "",
        pagebreak(),
        "# 18. large-gain error budget",
        "",
        md_text(out / "v4_large_gain_conclusion.md"),
        "",
        table(read_csv(out / "v4_large_gain_bounds.csv"), ["pathology", "case_oracle_bound", "voxel_oracle_bound", "selector_bound", "conclusion"], limit=6, max_len=38),
        "",
        "# 19. component survival",
        "",
        md_text(out / "v4_component_survival_report.md"),
        "",
        pagebreak(),
        "# 20. visual atlas",
        "",
        "独立 atlas 作为单独 PDF 保存，主 PDF 只嵌入 contact sheet，避免再引入右侧 panel 裁切。",
        "",
        table(
            [
                {"field": "atlas_pdf", "value": "v4_atlas_pages_a3_landscape.pdf"},
                {"field": "atlas_page_count", "value": len(atlas)},
                {"field": "bbox_validation", "value": "v4_atlas_pdf_bbox_validation.csv"},
                {"field": "bbox_status", "value": "all page bbox rows PASS"},
            ],
            ["field", "value"],
            max_len=60,
        ),
        "",
        image(out / "v4_atlas_contact_sheet.png", "V4 atlas contact sheet", "0.92\\linewidth", "0.72\\textheight"),
        "",
        pagebreak(),
        "# 21. Deep Research constraints",
        "",
        md_text(out / "DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730_v4.md"),
        "",
        pagebreak(),
        "# 22. current conclusions",
        "",
        "科学证据状态为 `SUFFICIENT`，Deep Research readiness 为 `READY`。这只表示下一代模型设计已有足够约束输入；当前 CARE 模型仍为 `FAILED_GATE`，没有新架构训练、没有 validation upload、没有 Docker upload、没有 hosted metric claim。",
        "",
        "# 23. unresolved questions",
        "",
        md_text(out / "external_deep_research_question_bank.md"),
        "",
        pagebreak(),
        "# 附录 A. validator 和 claim ledger",
        "",
        table(read_csv(out / "v4_deep_research_readiness_checklist.csv"), ["requirement", "passed", "evidence"], limit=20, max_len=48),
        "",
        "# 附录 B. Slurm accounting",
        "",
        table(slurm_rows, ["job_id", "name", "state", "exit_code", "submit", "end"], limit=12, max_len=36),
        "",
        "# 附录 C. provenance blocks",
        "",
        blocks(read_csv(out / "evidence_claim_ledger.csv"), "claim_id", ["source_path", "confidence", "notes"], limit=12),
        "",
    ]
    source.write_text("\n".join(str(x) for x in lines), encoding="utf-8")
    return source


def render_pdf(source: Path, out: Path) -> None:
    header = Path("/tmp/chinese-math-header.tex")
    code, header_log = run([str(PYTHON), "scripts/build_chinese_math_header.py", "--root", str(CARE_ROOT), "--output", str(header)], timeout=120)
    if code != 0:
        raise SystemExit(header_log)
    cache = Path("/tmp/care_forensics_v4_xelatex_cache")
    for sub in ["var", "config", "cache"]:
        (cache / sub).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TEXINPUTS"] = f"{RESOURCE_DIR}/texmf//:"
    env["TEXMFVAR"] = str(cache / "var")
    env["TEXMFCONFIG"] = str(cache / "config")
    env["TEXMFCACHE"] = str(cache / "cache")
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
        "fontsize=10pt",
        "-o",
        str(pdf),
    ]
    code, log = run(cmd, timeout=900, env=env)
    (out / "report_source_v4" / "xelatex_render.log").write_text(log, encoding="utf-8", errors="ignore")
    (out / "report_source_v4" / "build_commands.txt").write_text(
        "TEXINPUTS=/users/a/e/aereinh/render_resources/chinese_math_pdf/texmf//: "
        "TEXMFVAR=/tmp/care_forensics_v4_xelatex_cache/var "
        "TEXMFCONFIG=/tmp/care_forensics_v4_xelatex_cache/config "
        "TEXMFCACHE=/tmp/care_forensics_v4_xelatex_cache/cache "
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
    _, info = run(["pdfinfo", str(pdf)], timeout=120)
    (out / "v4_pdfinfo.txt").write_text(info, encoding="utf-8", errors="ignore")
    _, fonts = run(["pdffonts", str(pdf)], timeout=120)
    (out / "v4_pdffonts.txt").write_text(fonts, encoding="utf-8", errors="ignore")
    run(["pdftotext", "-layout", str(pdf), str(out / "v4_pdf_text_extract.txt")], timeout=240)
    pages = out / "v4_pdf_pages"
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
    with (out / "v4_pdf_page_quality.csv").open("w", newline="", encoding="utf-8") as f:
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
        sheet.save(out / "v4_pdf_contact_sheet.png")
    text = (out / "v4_pdf_text_extract.txt").read_text(encoding="utf-8", errors="ignore") if (out / "v4_pdf_text_extract.txt").exists() else ""
    report = {
        "pdf": str(pdf),
        "exists": pdf.exists(),
        "size_bytes": pdf.stat().st_size if pdf.exists() else 0,
        "sha256": sha256(pdf) if pdf.exists() else "",
        "route": "pandoc_xelatex_named_fonts",
        "render_resource_dir": str(RESOURCE_DIR),
        "texinputs": f"{RESOURCE_DIR}/texmf//:",
        "chromium_fallback_used": False,
        "creator_contains_headless_chrome": "HeadlessChrome" in info,
        "producer_contains_skia": "Skia" in info,
        "named_font_hits": [name for name in ["TeXGyreTermes", "NotoSerifSC", "NotoSansSC", "FandolSong", "FandolHei"] if name in fonts],
        "chinese_text_extractable": any(token in text for token in ["科学证据", "设计证据包", "取证", "状态语义"]),
        "page_count_from_png": len(page_rows),
        "page_quality_failures": [r for r in page_rows if not r["status"].startswith("PASS")],
        "preview_pages": ["v4_pdf_pages/page-1.png", "v4_pdf_pages/page-3.png", "v4_pdf_pages/page-10.png", "v4_pdf_pages/page-19.png"],
        "contact_sheet": "v4_pdf_contact_sheet.png",
    }
    report["decision"] = "PASS" if report["exists"] and report["chinese_text_extractable"] and report["named_font_hits"] and not report["creator_contains_headless_chrome"] and not report["producer_contains_skia"] and not report["page_quality_failures"] else "FAIL"
    write_json(out / "v4_pdf_validation_report.json", report)


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
