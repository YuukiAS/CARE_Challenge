# Controller Notifications

Standalone controller goal notification service. It no longer depends on the route watchboard renderer or tmux session. `start_in_tmux.sh` opens or restarts a `Notifier` window inside a dedicated `care_notifier` session, creating that session when needed.

## Configure Email

Create an untracked env file at `secrets/care_notify.env`:

```bash
CARE_NOTIFY_SMTP_USER=humc2013@gmail.com
CARE_NOTIFY_SMTP_PASSWORD=<gmail_app_password>
```

The default recipient and SMTP settings are in `config.example.json`. The default monitored route list is now `main` only; historical `route_A`, `route_B`, and `route_C` remain configured but disabled unless a future handoff explicitly reactivates a route controller. Email is sent as `plain_plus_html`: a short Chinese decision brief plus an HTML alternative. The body intentionally omits token counts, long goal prompts, and Markdown tables. `email.max_important_slurm_jobs` limits how many Slurm jobs are expanded in the body, but credited `COMPLETED` jobs with elapsed runtime are always included before failed/cancelled attempts are truncated.

## Controller completion brief

For main-controller batches, the controller must write a concise terminal brief before marking the goal complete or blocked:

```text
results/<task>/notification_brief.json
```

Required fields are `task_name`, `final_status`, `commit_status`, `push_status`, `key_conclusion`, `blocked_or_failure_reason`, `slurm_terminal_status`, `evidence_paths`, and `next_step`. The watcher refuses to send a main completion email if this file is missing or if any brief value still contains `PENDING`, `RUNNING`, `NEEDS_MONITOR`, `JOB_SUBMITTED`, or `AWAITING_SACCT`. This keeps submitted-only and monitor packets from producing completion emails.

## Checks

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once --dry-run
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --send-test --dry-run
bash controller_notifications/start_in_tmux.sh --dry-run
```

After `secrets/care_notify.env` is configured, send one real test email. The test uses the same Chinese summary-first format as live controller terminal notifications, including controller status, key evidence, and a Slurm job summary read from packet evidence. It does not print SMTP passwords or secrets, and it does not imply Route C is active unless `enabled_routes` explicitly includes it.

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --send-test
```


The default email body avoids Markdown-only tables so plain-text email clients remain readable. It does not include watchboard links.

Then start the persistent watcher:

```bash
bash controller_notifications/start_in_tmux.sh
```

The watcher sends email only after it has already observed a controller goal in a non-terminal state and later sees `complete` or `blocked`. Existing terminal goals at first startup are recorded as baseline state, not backfilled as old notifications.

## Health

Each scan writes a status JSON without secret values:

```text
controller_notifications/state/notify_goal_watcher_status.json
```

The status records last scan time, discovered goal sources, pending events, enabled routes, state/log paths, last sent or failed email summary, and SMTP secret presence as booleans only. Email failures are recorded and the loop continues; config-level send blockers are shown as `blocked_config`.

The persistent log is:

```text
controller_notifications/logs/notify_goal_watcher.log
```
