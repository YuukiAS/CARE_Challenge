# scar evidence brief

1. 数据规模：总病例 220；raw/meta T2-present 病例 80。
2. 可靠标签：scar 使用 label 5；pure edema 使用 label 4 且仅在 raw/meta T2-present 病例作为 official edema。
3. 模态信息：不能从 Dataset501 三通道 slot 推断 T2/C0 可用性。
4. nnU-Net 失败：主要表现为病例级 FN/FP、边界和小病灶误差；完整 decoder/recipe 是强基线条件。
5. MoSAIC 失败：clean OOF 与 full-data/hosted-near recipe 必须分层，不能混写。
6. CARE 历史失败：组件名不等于 final-logits effect，必须绑定 prediction/casewise/help-harm。
7. lesion morphology：V3 manifest 提供 component count 和体素量。
8. feature separability：当前 proxy 证据不足，activation hook 是 V3 未决执行项。
9. oracle：case oracle 只支持有限 selector 上限，voxel oracle 不可部署。
10. center/domain：center 与 modality availability 强相关，需防 center shortcut。
11. alignment：complete tri-modal alignment 不能被旧 safe-subset smoke 替代。
12. valid historical experience：保留数据 hygiene、bounded correction、final-output trace 和 decoder preservation。
13. forbidden repeated mistakes：禁止 no-T2 假阴性监督、edema-zone 冒充 official edema、full-data 冒充 clean。
14. plausible high-gain mechanisms：必须直接覆盖 error pool 并有 patient-level probe 支持。
15. unresolved questions：activation separability、clean external domain、hosted recipe provenance 仍需严格绑定。
