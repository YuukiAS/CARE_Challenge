当前 PRISM v2 已经有一版部分实现骨架，但训练前最关键的强初始化证据没有成立，因此不能进入 400 步预训练前检查，更不能启动 fold0 正式训练。问题不是模型指标失败，而是同折 ResidualEncoderUNet checkpoint 资产缺失：仓库有 ResEnc plans，可实例化真实结构，但没有找到可用于字节移植和 FP32 奇偶校验的同折 ResEnc checkpoint。

```text
phase: W1_EXACT_IMPLEMENTATION
status: FAIL_CLOSED
failure_class: EXECUTION_OR_INIT
blocking_gate: same-fold ResEnc checkpoint transplant and FP32 parity
W2_allowed: false
new_slurm_job_allowed: false
```

Partial implementation files:

- `src/care_myocardium/models/care_prism.py`
- `src/care_myocardium/training/care_prism_trainer.py`
- `src/care_myocardium/data/care_prism_dataset.py`
- `src/care_myocardium/inference/care_prism_predictor.py`

Controller rejects substituting `nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres` PlainConv checkpoints for the required ResEnc transplant gate.
