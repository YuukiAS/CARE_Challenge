# MMRD 可继承经验

MMRD 的可继承部分主要是数据规则：modality dropout、reliable-label mask、no-T2 edema loss hygiene 是必要边界，不应被写成单独模型增益。未来如果重测 distillation，必须同时绑定 teacher/student/checkpoint/prediction，并分别报告 scar 与 raw/meta T2-present official pure edema。
