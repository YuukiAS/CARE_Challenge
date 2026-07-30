# CARE failure forensics controller report

过去多次失败目前最可信的共同问题不是某一个新结构缺得不够多，而是评价语义、checkpoint/recipe 绑定、训练预算、decoder/reset 诊断和病例级 evidence 没有被同口径冻结。其中 pure edema 与 edema-zone 混写、full-data MoSAIC 冒充 clean comparison、pending/未完成诊断冒充完成，是必须先清除的取证错误。本包已经生成可搜索中文 PDF 和机器可读清单，但 strict validator 仍然返回 NEEDS_REPAIR，因为 GPU/forward/probe/decoder-reset 等关键诊断尚未 terminal。

controller_verification_decision: NEEDS_REPAIR
operational_completion_status: PARTIAL_PACKET_RENDERED
experiment_adequacy_decision: INADEQUATE_FOR_FINAL_SCIENTIFIC_DECISION
contract_compliance_status: NO_PUSH_NO_UPLOAD_NO_NEW_ARCHITECTURE
required_outputs_complete: PARTIAL
validators_passed: false
all_jobs_terminal: true
aggregation_complete: false
pdf_complete: true
pdf_searchable: true
pdf_visual_validation_complete: automated_page_render_only
claim_ledger_complete: partial
git_commit_decision: defer_until_strict_validator_passes
git_push_decision: forbidden_by_contract
next_required_action: run bounded forensic diagnostics or explicitly accept partial Deep Research packet
