# CARE-ASE Planning Review

review_type: independent_gpt_critic
reviewed_branch: main
reviewed_commit_after_revision: fa4be4ae44e2fd3fde206e6d572006d3b21e884d
review_decision: CARE_ASE_CONTROLLER_REVISE
execution_authorized: false
training_authorized: false

## 结论

原 CARE-ASE 方向正确，但不能直接批准执行。其主要问题不是缺少更多组件，而是合同矛盾会让实现再次落入 decoder 能力损失、no-T2 错误监督、fold 内数据泄漏、共享主干 checkpoint 拼接、可变 reviewer SHA 和 Slurm no-run。已落库 v2 蓝图、v2 exact contract、anatomy/reviewer amendment 与 revised controller draft；当前仍不得创建正式 Controller 或启动训练。

## 已落库的硬修订

1. **成熟 decoder 继承**：scar/edema 复制 stock 最高两级完整 decoder stages；anatomy 保留原 stock 最高两级路径。额外证据仅通过零初始化残差投影进入，三条路径 step0 logit parity 均 `<=1e-6`。禁止随机 anatomy decoder、固定 `64/32` 小头和 decoder reset。
2. **no-T2 监督闭环**：T2-present 使用六类竞争；no-T2 使用排除 class4 的五类竞争，class4 不进入 loss graph，edema-exclusive 参数梯度精确为0。
3. **无 fold 泄漏**：inner 从 development pool 固定分层抽取并完全退出训练；Stage C 只用各 fold `actual-train complete`，禁止 inner、outer 或全部80例。
4. **单一 checkpoint**：每 fold 只能选一个完整 checkpoint，禁止 scar/edema/anatomy 从不同 step 拼接共享参数。
5. **采样与 loss 无空白**：固定 context 物理距离、OOF component FN/FP 阈值、boundary target、extent empty-wall fallback、Dice/Tversky reduction 和 relation stop-gradient。
6. **单 Executor**：高耦合模型、loss、sampler、trainer 不再拆成三个无 executor plan 的并行 worktree；fold2/fold3 仅在 runtime 并行。
7. **No-Run 防线**：每 fold 七个 2000-step、单 job不超过8小时的 exact-resume chain；训练 `afterok`、finalizer `afterany`；htzhulab pending 2小时后自动加入 a100 mirror，24小时证据阈值前不得 scheduler block。
8. **无二次人工继续门**：未来正式授权在 W0 前一次性冻结权限；W2 PASS 后自动启动 W3，Stage A/B/C 均不可因低分跳过。
9. **固定审阅 SHA**：terminal aggregation/validator 后先建 local candidate commit；Reviewer 在只读 checkout 审该 SHA；PASS 后只能 push 同一 SHA，再核对 remote SHA 后通知。implementation revise 必须从最早受影响 wave 重跑。

## 下一轮复审必须确认

- 正式 Controller 的 reviewed commit、三份设计文件 SHA 与 frontmatter 完全一致；
- implementation validator 与 known-bad 真实覆盖上述九类失败；
- 正式授权字段、dependency finalizer、candidate-review-push 顺序与 notification 路径机器可解析；
- 当前 `DRAFT_REVISE_NOT_AUTHORIZED` 没有被误当作执行许可。
