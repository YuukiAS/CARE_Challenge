# CARE Route Watchboard

The route watchboard is a read-only browser view for the CARE route portfolio.
It is meant for status visibility only. It does not submit jobs, cancel jobs,
merge branches, upload packages, or mutate runtime state.

## Build

From the CARE root:

```bash
python scripts/ops/build_route_watchboard.py --user aereinh
```

This writes:

```text
results/watchboard/index.html
results/watchboard/status.json
```

The page includes:

- Route A/B/C purpose, branch, worktree, controller/reviewer tmux status, next
  gate, result packet presence, and architecture notes.
- Slurm jobs for the selected user, grouped by partition.
- `general` partition jobs as display-only connection/runtime jobs.
- Partition summary for visible CARE GPU partitions.
- Guardrail warnings for missing result roots, missing controllers, dirty
  worktrees, and other status signals.

## Serve For Codex App Browser

For local browsing on the server:

```bash
python scripts/ops/build_route_watchboard.py --user aereinh --serve --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/index.html
```

If the Codex App browser is running on a different machine than the CARE
server, use the existing tunnel or SSH port-forwarding mechanism to forward
server port `8765` to the browser environment.

## Safety

The watchboard intentionally has no action buttons. Commands such as `scancel`,
`sbatch`, `srun`, `git merge`, `git push`, and upload operations are forbidden
from this interface. Keep `general` partition jobs visible but never actionable,
because those jobs may keep the remote development connection alive.
