# CARE-ASE Planning Review

review_type: independent_gpt_critic
reviewed_branch: main
reviewed_commit_after_revision: bd6089fe954b9d33c05325ff11c11eb2a698ca06
review_decision: CARE_ASE_CONTROLLER_REVISE
execution_authorized: false
training_authorized: false

## 结论

原 CARE-ASE 方向正确，但不能直接批准执行。其主要问题不是缺少更多组件，而是若干合同矛盾会让实现再次落入 decoder 能力损失、no-T2 错误监督、fold 内数据泄漏、共享主干 checkpoint 拼接和 Slurm no-run。已落库 v2 蓝图、v2 exact contract 与 revised controller draft，用于下一轮独立复审；当前仍不得创建正式 Controller 或启动训练。

## 已修复的硬问题

1. **最高两级病理解码器只复制 classifier，仍会重复 ARC/PRISM 的 decoder reset。**  
   v2 改为完整复制 stock 最高两级 decoder stages，并以零初始化残差投影接入新证据；step0 class4/class5 logit parity 必须 `<=1e-6`。

2. **no-T2 仍通过无条件六类损失压低 edema。**  
   v2 改为 T2-present 六类竞争、no-T2 排除 class4 的五类竞争；edema-exclusive 参数梯度必须精确为0。

3. **Stage C 写成“80例完整病例”会污染 fold inner/outer。**  
   v2 固定为各 fold `actual-train complete`，并要求 train/inner/outer case-list/hash 和交集 fail-closed。

4. **scar/edema 分别选 step 与共享 encoder/decoder 不相容。**  
   v2 每 fold 只允许一个完整 checkpoint，以冻结 joint score 选择；禁止跨 step 参数拼接。

5. **hard-negative、boundary、extent、Dice/Tversky/relation 等语义留给 Codex。**  
   v2 固定物理距离阈值、component FN/FP 定义、empty-wall fallback、signed-distance target、loss reduction 与 stop-gradient 权限。

6. **三个 Executor 无 executor plan，且高耦合代码并行合并容易删模块。**  
   revised draft 改为单 Executor + Controller repair loop；fold2/fold3 仅作为 Slurm runtime 并行。

7. **18小时单 job、tmux watcher 和“若允许复用 interactive”仍可能 no-run。**  
   v2 改为每 fold 七个 2000-step、每 job 不超过8小时的 exact-resume chain；训练依赖 `afterok`，finalizer `afterany`；htzhulab pending 2小时后自动提交 a100 mirror，24小时证据阈值前不得 scheduler block。

8. **正式训练后还有 W7 人工授权门。**  
   revised draft 删除二次人工继续门；未来正式授权必须在 W0 前一次性冻结 commit/push/notify 权限。当前 draft 仍全部未授权。

## 下一轮复审必须确认

- v2 蓝图、v2 exact contract 与正式 Controller frontmatter/hash完全一致；
- implementation validator和known-bad真正覆盖上述八类失败；
- 正式授权字段、reviewer checkout、dependency finalizer与notification路径已机器可解析；
- 没有再把当前 draft 直接当作执行许可。
