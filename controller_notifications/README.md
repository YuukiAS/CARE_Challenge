# Controller Notifications

Standalone controller goal notification service. It is intentionally separate from the watchboard renderer, but it now publishes lightweight health for the watchboard ops layer. `start_in_tmux.sh` opens or restarts a `Notify` window inside the existing `care_watchboard` session; it never creates a separate ops session.

## Configure Email

Create an untracked env file at `secrets/care_notify.env`:

```bash
CARE_NOTIFY_SMTP_USER=humc2013@gmail.com
CARE_NOTIFY_SMTP_PASSWORD=<gmail_app_password>
```

The default recipient and SMTP settings are in `config.example.json`. The default monitored routes are Route B/C, while the config keeps `main`, `route_A`, `route_B`, and `route_C` sections for future rounds. Email is sent as `plain_plus_html`: a Chinese plain-text decision brief plus an HTML alternative for clients that render tables. `email.max_important_slurm_jobs` limits how many Slurm jobs are expanded in the body.

## Checks

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once --dry-run
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --send-test --dry-run
bash controller_notifications/start_in_tmux.sh --dry-run
```

After `secrets/care_notify.env` is configured, send one real test email. The test uses the same Chinese summary-first format as live controller terminal notifications, including controller status, a Route A/B/C overview, watchboard links, and a Slurm job summary read from route-local packet evidence. It does not print SMTP passwords or tunnel secrets.

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --send-test
```


The default email body includes the public and local watchboard links. It avoids Markdown-only tables so plain-text email clients remain readable:

```text
https://watchboard.httpwwwcardiacnexus-ukb.com/index.html
http://127.0.0.1:8766/index.html
```

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
