# soft-ROI refiner

## 历史分析原文迁移

## 5. Refiner 问题

### 5.1 scar / edema refiner 的结构差异已经有，但科学证据不足

代码里 scar 和 edema 的 refiner 确实不同：scar 是小 ROI / LGE-oriented / tighter crop；edema 是大 ROI / T2-conditioned / larger crop / no-T2 blocking。这符合示意图方向。

但是，M9 的 refiner evidence 仍然主要来自 ROI coverage、component rows、same-split metrics等聚合表。`m9_refiner_causal_effect.csv` 在 aggregator 中本质上由 component rows 写出，并不是真正的 refiner-on/off causal ablation。

M10 必须做真实 toggles：

```text
refiner_off
proposal_only
scar_refiner_only
edema_refiner_only
both_refiners_on
```

每个 toggle 都需要同一 checkpoint、同一 eval cases、同一 decode rule 的 final-label delta、Dice、HD95、remote-FP、component count。不能再把普通 component metric 表命名为 causal effect。

### Refiner 有结构差异，但没有被真正因果验证

代码里 scar 与 edema refiner 确实不同：

* scar 使用 LGE、小 ROI、小 crop；
* edema 使用 T2、大 ROI、大 crop，并有 no-T2 block。

但是当前 `m9_refiner_causal_effect.csv` 的生成方式未必是真正的 on/off inference ablation。如果只是把已有 component metric 汇总后命名为 causal effect，就无法知道 refiner 究竟是在改善 proposal、破坏 proposal，还是几乎没有改变 final labels。

因此 refiner 设计方向可能是对的，但当前实现和证据不足以证明其效果。
