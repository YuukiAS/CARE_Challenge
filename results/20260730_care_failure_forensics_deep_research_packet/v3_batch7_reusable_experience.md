# Batch7 可继承经验

V3 只能继承有路径证据的经验：强基线 final-mask ownership 必须明确；任何 router、dictionary、prototype、refiner 组件都必须证明进入 final logits 或 final mask；扩大结构化组件作用后如果 scar 变差，应优先检查 final-output ownership、训练预算、case help/harm 和 remote FP，而不是把概念直接判死。

禁止重复的错误是：用合理设计名词替代 final-logits 证据；把 mixed edema-zone 改善写成 official pure edema 改善；在 control 与 SRR 使用同一 prototype input 时解释为 prototype 无效。
