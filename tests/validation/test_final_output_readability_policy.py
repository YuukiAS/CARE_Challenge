from __future__ import annotations

from pathlib import Path

from scripts.validation import validate_handoff_policy as policy


def messages(text: str, name: str = "good_readability.md") -> list[str]:
    findings = policy.validate_final_output_readability(Path(f"tests/fixtures/readability/{name}"), text)
    return [finding.message for finding in findings]


def good_opening() -> str:
    return (
        "当前最重要的问题是训练目标还没有稳定约束最终预测结果，因为现有监督主要落在中间响应上，"
        "所以现在应当先用小规模实验确认梯度是否进入最终输出，暂时不要扩展更多 fold 或上传验证。"
    )


def test_natural_chinese_first_paragraph_passes() -> None:
    text = good_opening() + "\n\n这段结论先说明意义，再列出证据。"
    assert messages(text) == []


def test_first_paragraph_machine_style_starts_fail() -> None:
    bad_starts = [
        "/users/a/e/aereinh/CARE/results/x 表明需要修复。",
        "git status --short 之后可以继续。",
        "B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK 是当前问题。",
        "AWAITING_REVIEW 表示还不能继续。",
    ]
    for idx, text in enumerate(bad_starts):
        msgs = messages(text, f"bad_first_{idx}_readability.md")
        assert any("first paragraph starts" in msg for msg in msgs)


def test_internal_code_heading_fails() -> None:
    text = "# B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK\n\n" + good_opening()
    msgs = messages(text, "bad_heading_readability.md")
    assert any("used as heading" in msg for msg in msgs)


def test_internal_label_after_plain_explanation_passes() -> None:
    text = (
        "训练目标没有直接约束最终预测结果，这是当前最重要的问题，因为最终输出层拿不到足够稳定的监督。"
        "现在应当先验证梯度路径是否生效，暂时不要扩大训练规模（B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK）。"
    )
    assert messages(text) == []


def test_mechanism_without_problem_gap_flow_and_minimal_experiment_fails() -> None:
    text = good_opening() + "\n\n## 输出机制\n\n这里使用 final-objective repair，然后调大权重。"
    msgs = messages(text, "bad_mechanism_readability.md")
    assert any("mechanism explanation misses" in msg for msg in msgs)


def test_formula_without_before_and_after_explanation_fails() -> None:
    text = good_opening() + "\n\n$$\nL = x + y\n$$\n"
    msgs = messages(text, "bad_formula_readability.md")
    assert any("formula lacks" in msg for msg in msgs)


def test_training_stage_bare_checklist_fails() -> None:
    text = good_opening() + "\n\n## 训练阶段\n\n- Stage A\n- Stage B\n- Stage C\n"
    msgs = messages(text, "bad_training_readability.md")
    assert any("bare checklist" in msg for msg in msgs)


def test_technical_details_last_and_main_judgment_independent_passes() -> None:
    text = (
        good_opening()
        + "\n\n## 为什么现在需要处理\n\n这件事回答的是模型是否真的在优化最终预测，而不是只改善中间特征。"
        + "\n\n## 下一步最小行动\n\n先固定数据划分和训练预算，只改变最终输出监督路径；成功说明瓶颈在梯度连接，失败则说明中间表征本身不足。"
        + "\n\n## 技术细节\n\n```text\nresults/example/controller_report.md\npython scripts/validation/validate_handoff_policy.py --policy\n```\n"
    )
    assert messages(text) == []


def test_controller_report_must_not_start_with_machine_fields() -> None:
    text = """controller_verification_decision: VERIFIED_COMPLETE
operational_completion_status: COMPLETE
experiment_adequacy_decision: PASS
contract_compliance_status: PASS
required_outputs_complete: true
validators_passed: true
all_jobs_terminal: true
aggregation_complete: true
git_commit_decision: COMMIT_LOCAL_PACKET
git_push_decision: SKIP_PUSH
next_required_action: RETURN_TO_PLANNER
"""
    findings = policy.validate_final_output_readability(Path("results/example/controller_report.md"), text)
    assert any("first paragraph starts" in finding.message or "first paragraph does not explain" in finding.message for finding in findings)


def test_controller_report_with_human_intro_then_fields_passes() -> None:
    text = (
        good_opening()
        + "\n\n这些证据说明控制器已经检查了输出、验证器和作业状态，技术字段放在最后用于机器读取。"
        + "\n\ncontroller_verification_decision: VERIFIED_COMPLETE\n"
        + "operational_completion_status: COMPLETE\n"
        + "experiment_adequacy_decision: PASS\n"
        + "contract_compliance_status: PASS\n"
        + "required_outputs_complete: true\n"
        + "validators_passed: true\n"
        + "all_jobs_terminal: true\n"
        + "aggregation_complete: true\n"
        + "git_commit_decision: COMMIT_LOCAL_PACKET\n"
        + "git_push_decision: SKIP_PUSH\n"
        + "next_required_action: RETURN_TO_PLANNER\n"
    )
    findings = policy.validate_final_output_readability(Path("results/example/controller_report.md"), text)
    assert findings == []
