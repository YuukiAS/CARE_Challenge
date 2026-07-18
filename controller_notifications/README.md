# Controller Notifications

Standalone Route B/C controller goal notification service. It is intentionally separate from the watchboard renderer; the only tmux coupling is that `start_in_tmux.sh` opens a `Notify` window inside the existing `care_watchboard` session.

## Configure Email

Create an untracked env file at `secrets/care_notify.env`:

```bash
CARE_NOTIFY_SMTP_USER=humc2013@gmail.com
CARE_NOTIFY_SMTP_PASSWORD=<gmail_app_password>
```

The default recipient and SMTP settings are in `config.example.json`.

## Checks

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --once --dry-run
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --send-test --dry-run
bash controller_notifications/start_in_tmux.sh --dry-run
```

After `secrets/care_notify.env` is configured, send one real test email:

```bash
./envs/env_CARE/bin/python controller_notifications/notify_goal_watcher.py --send-test
```

Then start the persistent watcher:

```bash
bash controller_notifications/start_in_tmux.sh
```

The watcher sends email only after it has already observed a controller goal in a non-terminal state and later sees `complete` or `blocked`. Existing terminal goals at first startup are recorded as baseline state, not backfilled as old notifications.
