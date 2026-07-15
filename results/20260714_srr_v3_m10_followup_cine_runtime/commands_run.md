# Commands Run

See controller ledger and Slurm accounting for full monitor history.

Terminal accounting command:

```bash
sacct -j 58932590,58932609,58932626,58932627,58932628,58932629,58997393,58997394 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,Timelimit,NodeList -P
```

Checkpoint inspection command:

```bash
envs/env_CARE/bin/python - <<'PY'
from pathlib import Path
import torch
p=Path('results/20260714_srr_v3_m10_followup_cine_runtime/runtime/cine_temporal/variants/m10_cine_learned_temporal/checkpoints/checkpoint_best.pt')
print('exists', p.exists(), 'size', p.stat().st_size if p.exists() else 0)
if p.exists():
    ckpt=torch.load(p, map_location='cpu')
    print('keys', sorted(ckpt.keys()))
    for k in ['step','score']:
        print(k, ckpt.get(k))
PY
```

Checkpoint inspection output:

```text
exists True size 674149
keys ['model', 'score', 'step']
step 6000
score 0.9316869217072526
```
