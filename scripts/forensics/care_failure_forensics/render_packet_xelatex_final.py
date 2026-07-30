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
Noto_CJK_FONT = RESOURCE_DIR / "texmf/fonts/opentype/public/noto-cjk/NotoSerifSC-Regular.otf"
PYTHON = CARE_ROOT / "envs/env_CARE/bin/python"
PDF_NAME = "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730_v2.pdf"


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


def read_csv_all(path: Path, limit: int = 240) -> list[dict[str, str]]:
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


def table_appendix(title: str, rows: list[dict[str, str]], fields: list[str], chunk_size: int = 8) -> list[str]:
    if not rows:
        return []
    out: list[str] = [pagebreak(), f"# {title}", ""]
    for idx in range(0, len(rows), chunk_size):
        chunk = rows[idx : idx + chunk_size]
        if idx:
            out.extend([pagebreak(), f"# {title}（续 {idx // chunk_size + 1}）", ""])
        out.extend([compact_table(chunk, fields), ""])
    return out


def write_markdown(root: Path) -> Path:
    source = root / "report_source_v2" / "CARE_failure_forensics_20260730_v2.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = root / "figures"
    montage_sheet = root / "case_montages/contact_sheet_20_cases.png"
    model_rows = read_csv_rows(root / "model_lineage.csv", 12)
    historical_rows = read_csv_rows(root / "historical_experiment_inventory.csv", 12)
    survival_rows = read_csv_rows(root / "historical_component_survival_ledger.csv", 20)
    gain_rows = read_csv_rows(root / "large_gain_feasibility_analysis.csv", 10)
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
        "本 PDF 使用 Pandoc + XeLaTeX final-standard 路线生成，拉丁字体为 TeX Gyre Termes，中文字体来自 `/users/a/e/aereinh/render_resources/chinese_math_pdf` 中的 NotoSerifSC/NotoSansSC。它不是新模型蓝图，不包含 validation upload，也不声明 hosted 指标。",
        "",
        "## 一页执行摘要",
        "",
        "V2 的实际结论是：历史 CARE 路线长期未稳定超过 nnU-Net，主要不是某一个概念天然错误，而是强基线继承、decoder 完整性、final-mask 组件进入路径、病例级 help/harm 选择、标签/评价语义和训练/recipe 绑定没有同时闭合。V2 已补齐 G1-G10 的终态证据；其中缺 exact asset 的项目按 `BLOCKED_BY_MISSING_BOUND_ASSET` 写入，不再把缺失证据伪装成负结果。",
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
        "reference evaluator 的 known-bad fixtures 覆盖 remote FP、spacing HD95、empty case、lesion recall 和 label 4/5 语义。V2 对可绑定预测执行统一病例级重聚合；缺 exact asset 的旧模型不写成科学负结果。",
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
        "这些路线的历史证据等级不能混用。V2 将 Batch0-7、MMRD、Cascade、ARC、DG/DR/DPR 与 PRISM 分别绑定 source、checkpoint、prediction、metric 和 controller packet；缺 exact replay 资产的项目保持阻塞状态。",
        "",
        compact_table(historical_rows, ["model_id", "checkpoint_files_bound", "prediction_files_bound", "metric_files_bound", "terminal_status"]),
        "",
        evidence_blocks(model_rows, "model_id", ["result_evidence_grade", "current_scientific_conclusion"], limit=10),
        "",
        pagebreak(),
        "# 11. PRISM W1-W3 的完整复盘",
        "",
        "PRISM 不能只看是否有强 encoder。V2 已完成 13 checkpoint replay 和 D0-D3 decoder-reset 诊断。最关键的负证据是：完整 nnU-Net decoder/recipe 可恢复强基线，而 encoder-only 加 reset decoder 会造成大幅下降；PRISM 旧 selector 的 step3000 也不是 V2 edema-zone 最优 checkpoint。",
        "",
        compact_table(read_csv_rows(root / "nnunet_decoder_reset_real_summary.csv"), ["variant", "status", "case_count", "mean_scar_dice", "mean_pure_edema_dice"]),
        "",
        "# 12. MoSAIC clean、full-data 和 hosted recipe",
        "",
        "MoSAIC 必须拆成 clean OOF、full-data diagnostic 和 hosted-near recipe 三层。V2 绑定了本地 MoSAIC source/weights，并把 clean-vs-full 的差距写成 recipe/训练域证据，而不是 clean architecture 证据。",
        "",
        compact_table(read_csv_rows(root / "mosaic_recipe_decomposition_summary.csv", 12), ["variant", "scope", "case_count", "mean_scar_dice", "mean_pure_edema_dice"]),
        "",
        pagebreak(),
        "# 13-15. 统一病例级比较、困难子组和 help/harm",
        "",
        "统一病例级比较已在 nnU-Net OOF、MoSAIC clean OOF 和 PRISM/MoSAIC/历史可绑定证据之间分层完成。clean held-out 数字与 full-data 机制 probe 分开报告。",
        "",
        compact_table(read_csv_rows(root / "standardized_model_summary.csv", 12), ["model_id", "metric_name", "case_count", "mean_dice", "empty_pred_count"]),
        "",
        pagebreak(),
        "# 16. 失败病例视觉图册",
        "",
        "病例 montage 选取 20 个高互补/高分歧病例。红色为 scar，青色为 pure edema，黄色为 nnU-Net/MoSAIC disagreement。Codex 已打开 contact sheet 做真实视觉检查；完整单病例 PNG 保存在 `case_montages/`。",
        "",
        image(montage_sheet, "20 例病例 montage contact sheet", "98%"),
        "",
        "# 17. 错误重合和模型互补上限",
        "",
        "case oracle 对 nnU-Net 的直接提升很小，scar 约 0.022、pure edema 约 0.002、lesion union 约 0.013；voxel TP oracle 很高，但这是不可部署上限，不能当作模型性能。selector feasibility 显示 scar 有病例级可辨识信号，pure edema 证据弱。",
        "",
        compact_table(gain_rows, ["metric_name", "case_oracle_gain_vs_nnunet", "voxel_tp_oracle_gain_vs_nnunet", "deployable_selector_signal"]),
        "",
        "# 18. selector feasibility",
        "",
        "selector 只使用 prediction morphology/agreement features，固定 logistic regression 和 shallow gradient boosting，不使用神经网络 selector。scar selector AUROC 约 0.827；pure edema 因 MoSAIC-better 正例过少而阻塞。",
        "",
        pagebreak(),
        "# 19. 冻结特征可分性 probe",
        "",
        "第 19 页使用窄表/短字段，不使用会溢出的宽表。V2 绑定 MoSAIC coarse/scar fine component features 与 raw intensity controls；nnU-Net/PRISM frozen activation 未导出，因此按缺资产阻塞，不伪造成无信号。",
        "",
        compact_table(read_csv_rows(root / "feature_probe_summary.csv"), ["model_component", "status", "artifact_count", "notes"]),
        "",
        "# 20. decoder-reset 诊断对照",
        "",
        "D0-D3 的结论直接支持 PRISM 根因判断：完整 pretrained nnU-Net identity 可复现强基线；冻结 encoder 重置 decoder 后 pure edema 归零、scar 下降；top encoder 可恢复一部分；完整短 finetune 接近恢复。这说明 decoder/训练 recipe 是核心，不是只要 encoder 迁移就够。",
        "",
        "# 21-24. alignment、scar、pure edema 和 Cine",
        "",
        "alignment 绑定 20260703 complete-case 诊断，未支持多序列错位是主因。Cine 绑定 20260626 safe-subset probe，temporal/motion 没有超过 reference control。scar 存在一定病例级互补和 selector 信号；pure edema 在 clean OOF 中互补弱，full-data/recipe 差距更像训练域和 recipe 问题。",
        "",
        pagebreak(),
        "# 25. 为什么过去多次充分设计仍然失败",
        "",
        "目前最可信的共同原因是 evidence chain 不闭合：模块是否进入 final logits、loss 是否进入 total loss、checkpoint 是否可绑定、训练预算是否足额、评价对象是否混写，这些问题常常比设计名词更关键。组件生存清单把“思想有效、实现失败、未验证、思想失败”分开记录。",
        "",
        compact_table(survival_rows, ["source_model", "component", "future_status", "risk_of_repeating_failure"]),
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
        "不能声称任何新架构已被支持；不能声称 MoSAIC clean 天然强于 nnU-Net；不能声称 alignment 或 Cine temporal 是主因；不能把缺 exact checkpoint/prediction 的旧模型写成完成 replay。",
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
        compact_table(read_csv_rows(root / "historical_checkpoint_binding.csv", 20), ["model_id", "artifact_type", "path", "binding_status"]),
        "",
        pagebreak(),
        "# 附录 B：指标公式和 known-bad",
        "",
        evidence_blocks(claim_rows, "claim_id", ["source_path", "confidence", "notes"], limit=12),
        "",
        pagebreak(),
        "# 附录 C：Slurm 和运行回执",
        "",
        "本次 PDF 重渲染没有提交新的 Slurm job。已有 packet 的 controller context 和 V2 GPU manifest 记录了启动时可见的 Slurm 状态、G1-G4 GPU steps 与 G5-G10 聚合状态。",
        "",
        compact_table(read_csv_rows(root / "controller_ledger.csv", 12), ["timestamp_utc", "phase", "decision", "next_action"]),
        "",
        pagebreak(),
        "# 附录 D：完整病例级表格索引",
        "",
        "完整病例级重聚合已在 V2 可绑定证据范围内完成。这里列出机器可读表的位置和状态，不展开长路径列，避免 PDF 裁切。",
        "",
        compact_table(
            [
                {"file": "standardized_casewise_metrics.csv", "status": "COMPLETED_FOR_BOUND_NNUNET_MOSAIC_OOF"},
                {"file": "case_oracle_summary.csv", "status": "COMPLETED_FOR_BOUND_NNUNET_MOSAIC_OOF"},
                {"file": "historical_result_comparability.csv", "status": "COMPLETED_FOR_AVAILABLE_HISTORICAL_METRICS"},
                {"file": "prism_corrected_casewise_metrics.csv", "status": "COMPLETED_FOR_13_CHECKPOINT_REPLAY"},
            ],
            ["file", "status"],
        ),
        "",
    ]
    lines += table_appendix(
        "附录 E1：standardized casewise metrics 分块",
        read_csv_all(root / "standardized_casewise_metrics.csv", 96),
        ["case_id", "center", "metric_name", "model_id", "dice", "empty_pred"],
        8,
    )
    lines += table_appendix(
        "附录 E2：case oracle 和 voxel oracle 分块",
        read_csv_all(root / "case_oracle_summary.csv", 96),
        ["case_id", "center", "metric_name", "best_case_model", "case_oracle_dice", "voxel_tp_oracle_dice"],
        8,
    )
    lines += table_appendix(
        "附录 E3：PRISM 13 checkpoint corrected metrics 分块",
        read_csv_all(root / "prism_corrected_casewise_metrics.csv", 96),
        ["checkpoint_step", "case_id", "metric_name", "dice", "anchor_dice", "dice_delta_vs_anchor"],
        8,
    )
    lines += table_appendix(
        "附录 E4：Batch0-7 / SRR casewise metrics 分块",
        read_csv_all(root / "batch0_7_casewise_results.csv", 88),
        ["case_id", "pathology", "anchor_dice", "srr_dice", "dice_delta_srr_minus_anchor", "srr_hd95"],
        8,
    )
    lines += table_appendix(
        "附录 E5：ARC casewise metrics 分块",
        read_csv_all(root / "arc_casewise_metrics.csv", 72),
        ["case_id", "variant", "pathology", "dice", "hd95", "changed_mask_ratio_vs_nnunet"],
        8,
    )
    lines += table_appendix(
        "附录 E6：历史 prediction binding 分块",
        read_csv_all(root / "historical_prediction_binding.csv", 72),
        ["model_id", "artifact_type", "path", "binding_status"],
        8,
    )
    lines += table_appendix(
        "附录 E7：组件生存清单分块",
        read_csv_all(root / "historical_component_survival_ledger.csv", 40),
        ["source_model", "component", "casewise_signal", "failure_mode", "future_status"],
        8,
    )
    lines += [
        pagebreak(),
        "# 附录 E：代码、配置、split 和预测 hash",
        "",
        "当前 hash manifest 是启动级定位清单。大型 checkpoint 和 prediction 在 V2 中保留 path/size 绑定；关键 source 和小文件保留 SHA。缺 exact replay 条件的模型在对应 binding 表中标注。",
        "",
        compact_table(read_csv_rows(root / "hash_manifest.csv", 12), ["path", "hash_status", "size_bytes"]),
        "",
        pagebreak(),
        "# 附录 F：证据缺口",
        "",
        "V2 的缺口不再是 REQUIRED GPU 未运行，而是后续科学设计前的边界：不能把 oracle 写成可部署性能，不能把 full-data MoSAIC 写成 clean 架构优势，不能复制历史失败实现。",
        "",
        pagebreak(),
        "# 附录 G：PDF 渲染验收记录",
        "",
        "最终 PDF 采用 `pandoc_xelatex_named_fonts`，不是 Chromium fallback。验收重点是 `pdfinfo` 不含 HeadlessChrome/Skia，`pdffonts` 出现 TeXGyreTermes 与 `/users` render bundle 的 NotoSerifSC/NotoSansSC，`pdftotext -layout` 中文可抽取，第 1、3、10、19 页 PNG 中中文和表格可见。",
        "",
    ]
    source.write_text("\n".join(lines), encoding="utf-8")
    return source


def render_xelatex(root: Path, source: Path) -> None:
    header = Path("/tmp/chinese-math-header.tex")
    if not Noto_CJK_FONT.exists():
        raise SystemExit(f"Viewer-compatible /users CJK font not found: {Noto_CJK_FONT}")
    code, header_out = run([str(PYTHON), "scripts/build_chinese_math_header.py", "--root", str(CARE_ROOT), "--output", str(header)])
    if code != 0:
        raise SystemExit(header_out)
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
    (root / "report_source_v2" / "xelatex_final_render.log").write_text(out, encoding="utf-8", errors="ignore")
    (root / "report_source_v2" / "build_commands.txt").write_text(
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

    source = root / "report_source_v2" / "CARE_failure_forensics_20260730_v2.md"
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
    payload["cjk_font"] = str(Noto_CJK_FONT)
    payload["droid_fallback_used"] = False
    payload["chromium_fallback_used"] = False
    (root / "v2_pdf_validation_report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
