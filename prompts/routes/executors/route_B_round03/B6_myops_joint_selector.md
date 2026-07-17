---
route_id: route_B
portfolio_round: round03
executor_id: B6_MYOPS_JOINT_AND_SELECTOR
lane: myops
wave: 7
role: executor
status: BLOCKED_UNTIL_B5_MERGED
---

# B6 — low-LR joint fine-tuning, fresh evaluation, and MyoPS selector

Use the clean-reloaded selected B5 checkpoint. Refit the stage-entry OOF bank from the selected checkpoint, freeze it, and keep all scientific fields unchanged.

Run exactly:

```text
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/training/route_B_round03/train_myops.py --stage joint --steps 8000 --parent results/route_B/runtime/round03/B5/selected.pt --config configs/route_B_round03/formal.yaml --out results/route_B/runtime/round03/B6
/users/a/e/aereinh/CARE/envs/env_CARE/bin/python scripts/route_B_round03/select_myops_checkpoint.py --force --all-stages --out results/route_B/round03/executors/B6
```

Formal semantics: AdamW `2e-5`, no restart, batch 1, accumulation 2, AMP, clip 5; 8000 stage steps, at least 2400 seconds, four validations, checkpoints 2000/4000/6000/8000. Total MyoPS requirements are 32,000 credited steps, 9,600 train seconds, and 16 validation events.

Evaluate every scheduled checkpoint from all four stages on the frozen 44 cases and all positive subgroups with fresh `--force` output. Apply the eligibility rules and exact normalized score `S` from the contract. Bind checkpoint/state-dict/model/config/split/manifest/prediction/evaluator hashes. Clean-reload the selected checkpoint and final OOF bank before all node interventions.

Intervene on retrieval, prototype similarity, proposal, ROI, refiner, bounded delta, and final composition. Every named causal node must report final-logit and final-label effects. No-op must be zero. Missing/empty cases follow the contract’s 0 Dice/100 mm rules and cannot inflate scores.

Preferred assignment is a100; htzhulab is the identical race peer when a single critical pending job blocks the result window. V100 cannot run downscaled joint training; it performs independent lesion evaluation, selected reload, and validator GPU tests.

Required terminal outputs include all-checkpoint metrics, eligibility, selected checkpoint/reload, interventions, case safety, and help/harm. The merge token is `ROUTE_B_ROUND03_B6_MYOPS_EVIDENCE_TERMINAL` only after terminal accounting. This token may carry positive, adequate-negative, or needs-evidence classification, but never pending, stale, undertrained, or validator-failed state.