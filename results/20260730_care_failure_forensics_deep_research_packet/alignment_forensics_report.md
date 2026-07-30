# Alignment V2 forensic binding

V2 绑定 20260703 MyoPS complete-case alignment gate，而不是重新解释占位文件。

- registration rows: 32
- complete cases: 16
- component metric rows: 32
- subgroup rows: 10

结论边界：该 gate 的 Phase 1 没有支持多序列错位是主瓶颈；translation/slice/TPS/deformable 路线因此未继续执行，不能反向声明 alignment 修复有主要增益。
