# 冻结特征 probe 解释

V3 已把 V2 的 feature-probe 缺口升级为显式执行要求：如果 checkpoint 和代码可加载，必须用只读 forward hook；如果不可加载，必须记录 expected architecture、actual keys、missing/unexpected keys、shape mismatch 和 attempted environments。当前已绑定的 V2 probe 只能作为有限 proxy 证据，不能证明 nnU-Net/PRISM/MoSAIC activation family 没有信号。
