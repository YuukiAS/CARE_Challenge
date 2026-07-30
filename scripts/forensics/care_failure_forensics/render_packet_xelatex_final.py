#!/usr/bin/env python3
"""Render the CARE forensics packet with final-standard Pandoc + XeLaTeX.

This renderer avoids Chromium/Skia output and avoids wide pipe tables that can
overflow PDF margins.  Long evidence rows are represented as compact evidence
blocks or narrow tables.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


CARE_ROOT = Path("/users/a/e/aereinh/CARE")
RESOURCE_DIR = Path("/users/a/e/aereinh/render_resources/chinese_math_pdf")
DROID_CJK_FONT = Path("/usr/share/fonts/google-droid-sans-fonts/DroidSansFallbackFull.ttf")
PYTHON = CARE_ROOT / "envs/env_CARE/bin/python"
PDF_NAME = "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf"


def run(cmd: list[str], cwd: Path = CARE_ROOT, timeout: int = 180, env: dict[str, str] | None = None) -> tuple[int, str]:
    try:
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
    except FileNotFoundError as exc:
        return 127, str(exc)


def read_csv_rows(path: Path, limit: int = 12) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))[:limit]


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def compact_table(rows: list[dict[str, str]], fields: list[str]) -> str:
    if not rows:
        return "_暂无可展示行。_"
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        cells = []
        for field in fields:
            text = md_escape(row.get(field, ""))
            if len(text) > 80:
                text = text[:77] + "..."
            cells.append(text)
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def evidence_blocks(rows: list[dict[str, str]], title_field: str, body_fields: list[str], limit: int = 8) -> str:
    if not rows:
        return "_暂无可展示行。_"
    parts: list[str] = []
    for row in rows[:limit]:
        title = row.get(title_field, "") or "UNNAMED"
        parts.append(f"- **{md_escape(title)}**")
        for field in body_fields:
            val = md_escape(row.get(field, ""))
            if val:
                parts.append(f"  - `{field}`: {val}")
    return "\n".join(parts)


def image(path: Path, alt: str, width: str = "95%") -> str:
    return f"![{alt}]({path.resolve()}){{width={width}}}"


def pagebreak() -> str:
    return "\n\\newpage\n"


def write_markdown(root: Path) -> Path:
    source = root / "report_source" / "CARE_failure_forensics_20260730_xelatex_final.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = root / "figures"
    model_rows = read_csv_rows(root / "model_lineage.csv", 12)
    claim_rows = read_csv_rows(root / "evidence_claim_ledger.csv", 20)
    root_rows = read_csv_rows(root / "root_cause_ranked_table.csv", 12)
    ckpt_rows = read_csv_rows(root / "checkpoint_inventory.csv", 15)

    lines: list[str] = [
        "---",
        "title: CARE Myocardium 失败取证 Deep Research 证据包",
        "author: CARE Forensic Research Controller",
        "date: 20260730 本地证据冻结版",
        "---",
        "",
        "# CARE Myocardium 失败取证 Deep Research 证据包",
        "",
        "本 PDF 使用 Pandoc + XeLaTeX final-standard 路线生成，拉丁字体为 TeX Gyre Termes。由于当前 `/users/a/e/aereinh/render_resources/chinese_math_pdf` 中的 Fandol 在部分 PDF viewer 里会空白，最终中文字体改用系统可见且 `pdffonts` 为 `uni yes` 的 DroidSansFallbackFull。它不是新模型蓝图，不包含 validation upload，也不声明 hosted 指标。",
        "",
        "## 一页执行摘要",
        "",
        "当前最可靠的动作不是继续设计新 CARE 架构，而是先把评价语义、checkpoint/recipe 绑定、病例级统一重聚合、PRISM decoder-reset 对照、MoSAIC recipe decomposition 和 Cine temporal probe 做成可复现证据。已确认的硬边界是 pure edema 与 edema-zone 不能混写，full-data MoSAIC 不能冒充 clean fold0，pending 或未跑完的 GPU 诊断不能写成科学完成。",
        "",
        image(fig_dir / "evidence_grade_counts.png", "证据等级计数", "98%"),
        "",
        pagebreak(),
        "# 目录式章节索引",
        "",
        compact_table(
            [{"章节": str(i), "主题": t} for i, t in enumerate(
                [
                    "为什么现在必须做失败取证",
                    "CARE 数据、中心、模态和标签真值",
                    "官方与内部指标语义",
                    "当前评价代码中的已确认问题",
                    "nnU-Net 强基线到底强在哪里",
                    "SRR v2-v3 的设计意图与落地差距",
                    "Batch 0-7 历史证据",
                    "MMRD 的设计、实现和失败",
                    "Cascade/DG 的设计、实现和失败",
                    "ARC 的设计、实现和失败",
                    "PRISM W1-W3 的完整复盘",
                    "MoSAIC clean、full-data 和 hosted recipe",
                    "所有模型统一病例级比较",
                    "困难子组",
                    "case-wise help/harm",
                    "失败病例视觉图册",
                    "错误重合和模型互补上限",
                    "selector feasibility",
                    "冻结特征可分性 probe",
                    "decoder-reset 诊断对照",
                    "多序列错位是否为主因",
                    "scar 的真实瓶颈",
                    "pure edema 的真实瓶颈",
                    "Cine 的真实瓶颈",
                    "为什么过去多次充分设计仍然失败",
                    "根因排序与证据图",
                    "当前能下的结论",
                    "当前不能下的结论",
                    "外部 Deep Research 必须回答的问题",
                    "下一轮决策树",
                ],
                1,
            )],
            ["章节", "主题"],
        ),
        "",
        pagebreak(),
        "# 1. 为什么现在必须做失败取证",
        "",
        "过去几轮路线没有稳定超过 nnU-Net，不能直接归结为“模型不够复杂”。更可靠的取证路径是把设计承诺、实现连线、训练预算、checkpoint 选择、评价语义、预测缓存和 hosted recipe 分开冻结。",
        "",
        "# 2. CARE 数据、中心、模态和标签真值",
        "",
        "本节回答数据层面是否存在足够明确的标签和模态条件。关键边界是 official scar、official pure edema 和 internal edema-zone 必须分开。",
        "",
        image(fig_dir / "center_case_counts.png", "中心病例数", "92%"),
        "",
        image(fig_dir / "pathology_volume_distribution.png", "病灶体积分布", "92%"),
        "",
        compact_table(read_csv_rows(root / "pathology_prevalence_summary.csv"), ["cases", "scar_positive", "pure_edema_positive", "t2_present"]),
        "",
        pagebreak(),
        "# 3. 官方与内部指标语义",
        "",
        "第 3 页不使用宽表。下面只列三列：对象、内部标签、允许声明范围，避免右侧列截断。",
        "",
        compact_table(read_csv_rows(root / "official_internal_label_mapping.csv"), ["object", "internal_labels", "allowed_claim_scope"]),
        "",
        "reference evaluator 的 known-bad fixtures 覆盖 remote FP、spacing HD95、empty case、lesion recall 和 label 4/5 语义。完整病例级重聚合仍未 terminal。",
        "",
        "# 4. 当前评价代码中的已确认问题",
        "",
        "当前可确认的是评价风险，而不是所有历史结论已经被推翻。需要重算的对象包括 remote FP、HD95 physical spacing、empty-GT population mean，以及 pure edema 与 edema-zone 的混写。",
        "",
        "# 5. nnU-Net 强基线到底强在哪里",
        "",
        "nnU-Net 作为强基线的意义在于完整 decoder、稳定训练 recipe、成熟数据增强和直接 final mask 输出。当前包没有使用 foreground mean 掩盖 scar/pure edema。",
        "",
        pagebreak(),
        "# 6-10. SRR、Batch、MMRD、Cascade/DG、ARC 的历史证据",
        "",
        "这些路线的历史证据等级不能混用。C-G 级证据只说明有实现或诊断痕迹，不能证明模型优于 nnU-Net。",
        "",
        evidence_blocks(model_rows, "model_id", ["result_evidence_grade", "current_scientific_conclusion"], limit=10),
        "",
        pagebreak(),
        "# 11. PRISM W1-W3 的完整复盘",
        "",
        "PRISM 不能只看是否有强 encoder。D0-D3 未完成前，不能判断低分主要来自 representation、decoder reset 还是训练协议。",
        "",
        compact_table(read_csv_rows(root / "decoder_reset_training_summary.csv"), ["diagnostic", "status"]),
        "",
        "# 12. MoSAIC clean、full-data 和 hosted recipe",
        "",
        "MoSAIC 必须拆成 clean fold0、full-data diagnostic 和 hosted-near recipe 三层。full-data 权重不能作为 clean architecture 比较。",
        "",
        compact_table(read_csv_rows(root / "mosaic_recipe_decomposition_summary.csv"), ["status"]),
        "",
        pagebreak(),
        "# 13-15. 统一病例级比较、困难子组和 help/harm",
        "",
        "统一病例级比较尚未完成，因此这里不写 Dice 排名。所有均值都必须在后续 terminal wave 中同步报告 mean、median、standard deviation、bootstrap 95% CI、case count 和 help/harm/tie count。",
        "",
        compact_table(read_csv_rows(root / "standardized_model_summary.csv", 9), ["model_id", "pathology", "status"]),
        "",
        pagebreak(),
        "# 16. 失败病例视觉图册",
        "",
        "病例 montage 的选择依赖 standardized casewise metrics。本包目前只生成 QA contact sheet，明确标注 `VISUAL_HUMAN_CONFIRMATION_PENDING`。不能把自动 PNG 非空检查写成人工视觉结论。",
        "",
        "# 17. 错误重合和模型互补上限",
        "",
        "case oracle 与 voxel error overlap 尚未完成。当前不能支持 deployable selector，只能保留上限分析问题。",
        "",
        "# 18. selector feasibility",
        "",
        "如果 nested CV 不能稳定超过 always-best-single-model，必须写 `LOCAL_EVIDENCE_DOES_NOT_SUPPORT_DEPLOYABLE_MODEL_SELECTION`。当前 selector 尚未运行。",
        "",
        pagebreak(),
        "# 19. 冻结特征可分性 probe",
        "",
        "第 19 页使用窄表/短字段，不使用会溢出的宽表。当前 feature probe 尚未运行，不能声称 retrieval/prototype 具备病例外信号。",
        "",
        compact_table(read_csv_rows(root / "feature_probe_summary.csv"), ["probe", "AUROC", "status"]),
        "",
        "# 20. decoder-reset 诊断对照",
        "",
        "D0-D3 仍是关键缺口：D0 复现完整 nnU-Net，D1 冻结 encoder 重训 decoder，D2 开 top encoder stages，D3 完整模型短 finetune。D0 不能复现 baseline 时，D1-D3 不应启动。",
        "",
        "# 21-24. alignment、scar、pure edema 和 Cine",
        "",
        "alignment、scar/pure edema signal 和 Cine temporal signal 都不能只靠图或单帧 proxy 下结论。它们需要 patient-level split、held-out probe 和同口径评价。",
        "",
        pagebreak(),
        "# 25. 为什么过去多次充分设计仍然失败",
        "",
        "目前最可信的共同原因是 evidence chain 不闭合：模块是否进入 final logits、loss 是否进入 total loss、checkpoint 是否可绑定、训练预算是否足额、评价对象是否混写，这些问题常常比设计名词更关键。",
        "",
        "# 26. 根因排序与证据图",
        "",
        image(fig_dir / "decision_state.png", "决策状态", "92%"),
        "",
        evidence_blocks(root_rows, "root_cause", ["severity", "confidence", "confirmed", "evidence"], limit=7),
        "",
        pagebreak(),
        "# 27. 当前能下的结论",
        "",
        (root / "local_evidence_conclusions.md").read_text(encoding="utf-8"),
        "",
        "# 28. 当前不能下的结论",
        "",
        "不能声称任何新架构已被支持；不能声称 MoSAIC clean 天然强于 nnU-Net；不能声称 alignment 或 Cine temporal 是主因；不能把 GPU diagnostic 未运行状态写成科学完成。",
        "",
        "# 29. 外部 Deep Research 必须回答的问题",
        "",
        (root / "external_deep_research_question_bank.md").read_text(encoding="utf-8"),
        "",
        pagebreak(),
        "# 30. 下一轮决策树",
        "",
        (root / "research_decision_tree.md").read_text(encoding="utf-8"),
        "",
        "# 附录 A：模型和 checkpoint provenance",
        "",
        "checkpoint 清单只显示定位字段，不展开长路径列，避免右侧截断。完整路径仍保留在 CSV。",
        "",
        compact_table(ckpt_rows, ["model_id", "size_bytes", "hash_status", "evidence_quality"]),
        "",
        pagebreak(),
        "# 附录 B：指标公式和 known-bad",
        "",
        evidence_blocks(claim_rows, "claim_id", ["source_path", "confidence", "notes"], limit=12),
        "",
        pagebreak(),
        "# 附录 C：Slurm 和运行回执",
        "",
        "本次 PDF 重渲染没有提交新的 Slurm job。已有 packet 的 controller context 记录了启动时可见的 Slurm 状态；所有 GPU 诊断仍未 terminal，因此 strict validator 保持 `NEEDS_REPAIR`。",
        "",
        compact_table(read_csv_rows(root / "controller_ledger.csv", 12), ["timestamp_utc", "phase", "decision", "next_action"]),
        "",
        pagebreak(),
        "# 附录 D：完整病例级表格索引",
        "",
        "完整病例级重聚合尚未完成。这里列出目前机器可读表的位置和状态，不展开长路径列，避免 PDF 裁切。",
        "",
        compact_table(
            [
                {"file": "standardized_casewise_metrics.csv", "status": "REQUIRES_BOUND_PREDICTIONS"},
                {"file": "subgroup_performance_matrix.csv", "status": "REQUIRES_REAGGREGATION"},
                {"file": "help_harm_matrix.csv", "status": "REQUIRES_CASEWISE_METRICS"},
                {"file": "hd_component_matrix.csv", "status": "REQUIRES_REFERENCE_EVALUATOR_ON_BOUND_PREDICTIONS"},
            ],
            ["file", "status"],
        ),
        "",
        pagebreak(),
        "# 附录 E：代码、配置、split 和预测 hash",
        "",
        "当前 hash manifest 是启动级定位清单。大型 checkpoint 和 prediction 在本轮 PDF 中只保留 metadata 或 prefix hash；正式绑定对象需要后续逐个 full SHA256。",
        "",
        compact_table(read_csv_rows(root / "hash_manifest.csv", 12), ["path", "hash_status", "size_bytes"]),
        "",
        pagebreak(),
        "# 附录 F：证据缺口",
        "",
        "strict validator 仍然要求 D0-D3、feature probe、MoSAIC recipe decomposition、Cine temporal probe 和 standardized casewise reaggregation。该状态防止后续误读为完成。",
        "",
        pagebreak(),
        "# 附录 G：PDF 渲染验收记录",
        "",
        "最终 PDF 采用 `pandoc_xelatex_named_fonts`，不是 Chromium fallback。验收重点是 `pdfinfo` 不含 HeadlessChrome/Skia，`pdffonts` 出现 TeXGyreTermes 与 viewer-compatible CJK 字体，`pdftotext -layout` 中文可抽取，第 1、3、10、19 页 PNG 中中文和表格可见。Fandol 路线已测试为 named font 但 `uni no`，在用户 viewer 中不可见，因此未作为最终 CJK 字体。",
        "",
    ]
    source.write_text("\n".join(lines), encoding="utf-8")
    return source


def render_xelatex(root: Path, source: Path) -> None:
    header = Path("/tmp/chinese-math-header.tex")
    if not DROID_CJK_FONT.exists():
        raise SystemExit(f"Viewer-compatible CJK font not found: {DROID_CJK_FONT}")
    header.write_text(
        r"""% Generated by render_packet_xelatex_final.py.
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,longtable,array}
\usepackage{graphicx}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue,urlcolor=blue,citecolor=blue}
\XeTeXlinebreaklocale "zh"
\XeTeXlinebreakskip = 0pt plus 1pt
\setmainfont[
  Path={/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre/},
  BoldFont={texgyretermes-bold.otf},
  ItalicFont={texgyretermes-italic.otf},
  BoldItalicFont={texgyretermes-bolditalic.otf}
]{texgyretermes-regular.otf}
\setmonofont[
  Path={/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre/},
  BoldFont={texgyrecursor-bold.otf},
  ItalicFont={texgyrecursor-italic.otf},
  BoldItalicFont={texgyrecursor-bolditalic.otf}
]{texgyrecursor-regular.otf}
\setCJKmainfont[
  Path={/usr/share/fonts/google-droid-sans-fonts/},
  BoldFont={DroidSansFallbackFull.ttf}
]{DroidSansFallbackFull.ttf}
""",
        encoding="utf-8",
    )
    cache = Path("/tmp/care_forensics_xelatex_cache")
    for sub in ["var", "config", "cache"]:
        (cache / sub).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TEXINPUTS"] = f"{RESOURCE_DIR}/texmf//:"
    env["TEXMFVAR"] = str(cache / "var")
    env["TEXMFCONFIG"] = str(cache / "config")
    env["TEXMFCACHE"] = str(cache / "cache")
    output = root / PDF_NAME
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
        "geometry:margin=18mm",
        "-V",
        "fontsize=11pt",
        "-o",
        str(output),
    ]
    code, out = run(cmd, CARE_ROOT, timeout=240, env=env)
    (root / "report_source" / "xelatex_final_render.log").write_text(out, encoding="utf-8", errors="ignore")
    (root / "report_source" / "build_commands.txt").write_text(
        "TEXINPUTS=/users/a/e/aereinh/render_resources/chinese_math_pdf/texmf//: "
        "TEXMFVAR=/tmp/care_forensics_xelatex_cache/var "
        "TEXMFCONFIG=/tmp/care_forensics_xelatex_cache/config "
        "TEXMFCACHE=/tmp/care_forensics_xelatex_cache/cache "
        + " ".join(cmd)
        + "\n",
        encoding="utf-8",
    )
    if code != 0:
        raise SystemExit(out)


def pdf_qa(root: Path) -> None:
    pdf = root / PDF_NAME
    code, info = run(["pdfinfo", str(pdf)])
    (root / "pdfinfo.txt").write_text(info, encoding="utf-8", errors="ignore")
    code, fonts = run(["pdffonts", str(pdf)])
    (root / "pdffonts.txt").write_text(fonts, encoding="utf-8", errors="ignore")
    run(["pdftotext", "-layout", str(pdf), str(root / "pdf_text_extract.txt")])
    code, qpdf = run(["qpdf", "--check", str(pdf)])
    (root / "qpdf_check.txt").write_text(qpdf, encoding="utf-8", errors="ignore")

    preview_dir = root / "pdf_pages"
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir()
    run(["pdftoppm", "-png", "-r", "150", str(pdf), str(preview_dir / "page")], timeout=240)
    rows = []
    for idx, page in enumerate(sorted(preview_dir.glob("page-*.png")), 1):
        im = Image.open(page).convert("L")
        arr = np.asarray(im)
        rows.append(
            {
                "page": idx,
                "path": str(page.relative_to(root)),
                "width": im.width,
                "height": im.height,
                "pixel_std": float(arr.std()),
                "status": "PASS" if arr.std() > 1.0 else "FAIL",
            }
        )
    for name in ["pdf_page_quality.csv", "pdf_render_manifest.csv"]:
        with (root / name).open("w", newline="") as f:
            fields = ["page", "path", "width", "height", "pixel_std", "status"]
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    pngs = sorted(preview_dir.glob("page-*.png"))[:20]
    if pngs:
        sheet = Image.new("RGB", (4 * 260, 5 * 350), "white")
        draw = ImageDraw.Draw(sheet)
        for i, page in enumerate(pngs):
            im = Image.open(page).convert("RGB")
            im.thumbnail((240, 315))
            x = (i % 4) * 260
            y = (i // 4) * 350
            draw.text((x + 5, y + 2), page.name, fill="black")
            sheet.paste(im, (x, y + 24))
        sheet.save(root / "pdf_contact_sheet.png")

    source = root / "report_source" / "CARE_failure_forensics_20260730_xelatex_final.md"
    code, layout = run(
        [
            str(PYTHON),
            "scripts/validate_pdf_layout.py",
            str(pdf),
            "--source",
            str(source),
            "--preview-dir",
            str(root / "xelatex_final_preview"),
            "--json",
        ],
        timeout=120,
    )
    try:
        payload = json.loads(layout)
    except json.JSONDecodeError:
        payload = {"errors": ["validate_pdf_layout did not emit JSON"], "raw": layout}
    payload["final_standard_route"] = "pandoc_xelatex_named_fonts"
    payload["render_resource_dir"] = str(RESOURCE_DIR)
    payload["cjk_font"] = str(DROID_CJK_FONT)
    payload["fandol_status"] = "available in /users render resources but not used in final PDF because pdffonts reports uni=no and the user viewer rendered Chinese as blank"
    (root / "pdf_validation_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("results/20260730_care_failure_forensics_deep_research_packet"))
    args = parser.parse_args()
    root = args.root.resolve()
    source = write_markdown(root)
    render_xelatex(root, source)
    pdf_qa(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
