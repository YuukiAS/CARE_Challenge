# 训练证据与指标

> 历史快照：M09。本页只保存从 `todo-m10.md` 迁移来的原文段落；当前状态以 root wiki 和最新 review 为准。

## 1. 协议和证据层问题

---

### 1.2 Validator 不是 fail-closed

当前 M9 validator 对 ready packet 的 pending 状态扫描不充分。它主要扫描 top-level Markdown，不能可靠拒绝 required CSV/JSON 内的 unresolved 状态。M9 follow-up prompt 已经要求修复这一点：validator 必须扫描 Markdown、CSV、JSON，并且新增 stale-pending known-bad self-tests。

M10 前置门槛：任何 M10 prompt 之前，必须确认 M9 follow-up reviewer 判定 validator 已能 fail closed。

---

## 7. Metrics / aggregation 问题

---

## 10. M10 的可能路线

M10 必须根据 M9 follow-up reviewer 结论选择。
