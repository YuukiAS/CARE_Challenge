---
task_key: 20260805_public_repo_hygiene_and_architecture_assets
task_kind: maintenance
task_type: public_repository_hygiene_and_visual_asset_import
status: AUTHORIZED_BY_USER
risk_level: high
branch_policy: main_then_fast_forward_develop_if_safe
architecture_impact: none
scientific_decision_scope: none
execution_mode: controller_supervised
requires_execution_controller: true
controller_is_coordinator: true
allow_git_commit: true
auto_git_commit: true
allow_git_push: true
auto_git_push: true
allow_force_push: false
history_rewrite_authorized: false
training_authorized: false
outer_access_authorized: false
docker_build_or_upload_authorized: false
organizer_email_send_authorized: false
---

# Public CARE repository hygiene and architecture visual asset import

## Practical objective

The repository is now intentionally public. Perform one systematic repository audit and cleanup so that the public tree contains scientific source, reproducible lightweight evidence, protocols, documentation and publication figures, while server-local runtime state, credentials, personal operational configuration, bulky rerunnable outputs and unlicensed third-party assets remain only on the server.

Do not reopen the question of whether the repository should be public. The decision is final for this task.

## 1. Bootstrap and safety

Work from:

```text
/users/a/e/aereinh/CARE
```

Remote:

```text
YuukiAS/CARE_Challenge
```

Read the current remote `main`, `develop`, recent 20 commits, `AGENTS.md`, `START_HERE_FOR_GPT.md`, `GPT_PLANNER_CARE_PROTOCOL.md`, `prompts/AGENT_FLOW_V2_PROTOCOL.md`, `prompts/AGENT_FLOW_V3_PROTOCOL.md`, `prompts/routes/handoffs/CURRENT.md`, `.gitignore`, `.gitattributes`, root `README.md`, and the active automation/notifier files.

Before modifying tracked state:

1. ensure the local worktree is clean or record every pre-existing change;
2. create a server-local, ignored backup root:
   `/users/a/e/aereinh/.public-repo-cleanup/20260805_CARE/`;
3. copy every file that will be de-tracked into that backup while preserving relative paths;
4. record size and SHA256 before de-tracking;
5. never use `rm` for files that must remain on the server; use `git rm --cached` or move to the ignored local backup and restore a local working copy after the commit;
6. do not use `git clean`, destructive reset, force push or history rewriting.

## 2. Full tracked-tree inventory

Audit the exact tracked tree and all remote branches. Use machine-readable inventories based on at least:

- `git ls-files -s -z`;
- `git ls-tree -r -l main` and `develop`;
- `git rev-list --objects --all` plus `git cat-file --batch-check`;
- top current-tree files by size;
- top historical Git objects by size;
- tracked files that now match `.gitignore`;
- symlinks, submodules and Git LFS pointers;
- duplicate large files by SHA256;
- all tracked archives, weights, predictions, medical images, databases, logs, caches and generated build artifacts.

Write lightweight reports under:

```text
results/repository_hygiene/20260805_public_audit/
```

Required files:

```text
current_tree_inventory.csv
tracked_ignored_conflicts.csv
large_current_files.csv
large_historical_objects.csv
duplicate_files.csv
branch_inventory.md
```

Do not commit raw file contents or secret values into these reports.

## 3. Secret and personal operational information audit

Run a current-tree and Git-history scan using available local tools. Prefer `gitleaks git --no-banner --redact` when installed; otherwise install it only in a user-local temporary tool directory or use an equivalent read-only scanner. Also run targeted `git grep`/history searches for:

- private keys, PEM blocks and SSH material;
- access tokens, API keys, PATs, OAuth refresh tokens and cookies;
- `.env`, `.envrc`, auth JSON, credential stores and rclone configuration;
- SMTP/Gmail passwords or app passwords;
- database files containing Codex/session/runtime state;
- absolute home paths, host aliases, personal email addresses, phone numbers and user-specific tmux/runtime names;
- public Drive links and organizer email drafts when they are only operational delivery artifacts;
- local cluster node names, SSH configuration extracts and hidden host dependencies.

Classify findings as:

1. `SECRET_ROTATE_AND_ESCALATE` — a real credential or private key;
2. `DETRACK_LOCAL_ONLY` — server-local configuration/state/runtime evidence;
3. `PARAMETERIZE_AND_KEEP` — useful public code with hard-coded personal paths or addresses;
4. `HISTORICAL_EVIDENCE_KEEP` — non-secret historical scientific evidence whose operational paths are contextual only;
5. `FALSE_POSITIVE`.

If a real credential/private key is found in current or historical Git content:

- do not print it;
- record only file, commit, detector and redacted fingerprint;
- stop before cleanup publication with `NEEDS_HUMAN_SECRET_ROTATION_AND_HISTORY_REWRITE`;
- do not rewrite history or force push without a later explicit user authorization.

Write:

```text
secret_scan_summary.md
personal_operational_data_audit.csv
```

## 4. De-track policy

De-track from the public repository, while preserving locally on the server, any tracked instances of:

- raw CARE data, labels, NIfTI files or private derivatives;
- checkpoints, model weights, optimizer states, prototype banks and large caches;
- Docker archives, submission ZIP/TAR files and uploaded package copies;
- large logs, tmux captures, SQLite/runtime databases, Codex homes/state, notifier state and local locks;
- `.env*`, machine auth/config files, SSH/rclone/Gmail/SMTP configuration;
- generated predictions, full per-case runtime trees and reproducible bulky outputs;
- temporary packet bundles, duplicate exports and local-only workstation/server transfer archives;
- organizer email drafts and public-link receipts when they are operational delivery records rather than scientific documentation;
- third-party model assets or vendored code that lack a compatible redistribution license.

Keep public when appropriately licensed and useful:

- first-party source and tests;
- reproducible configs and wrappers without credentials;
- lightweight scientific result summaries and provenance receipts;
- challenge rules/links and anonymized methodology documentation;
- publication PDFs and architecture figures when redistribution is allowed;
- public automation protocols and generic scripts after personal values are parameterized;
- historical negative evidence needed to interpret the research, unless it contains personal or secret material.

Do not mass-delete scientific result summaries merely because they contain old absolute paths. Prefer parameterizing active files and documenting historical paths as historical. De-track only operationally sensitive or bulky material.

For every de-tracked file, add an exact ignore rule and record:

```text
path
reason
size
sha256
server_local_backup_path
public_replacement_or_summary
```

Write `detracking_manifest.csv`.

## 5. Parameterize active public code and documentation

At minimum audit and repair active files that currently expose user-specific operational values, including:

- `AGENTS.md`;
- root `README.md`;
- `controller_notifications/notify_goal_watcher.py` and its tracked configuration/docs;
- Agent-Flow v3 runtime layout and controller prompts;
- current automation scripts and examples.

Replace hard-coded active defaults such as `/users/a/e/aereinh/...`, `/home/yuukias/...`, a personal notification email, rclone remote names and tmux targets with environment variables, example configuration or repository-relative defaults where possible.

Keep a local ignored configuration example split:

```text
config/local/*.json        # ignored real values
config/examples/*.example.json  # tracked placeholders
```

Do not rewrite every historical result packet. Active entrypoints and public-facing documentation must be portable; historical evidence may retain clearly marked historical paths if non-secret.

Rewrite the root README as a public scientific/project landing page. Move server operations to a separate generic `docs/operations/LOCAL_SERVER_SETUP.md` using placeholders. Remove stale claims that Route A/B/C are current active development and point to current `main`/`develop` posture and Agent-Flow v3.

## 6. Third-party and licensing audit

Audit `third_party/`, copied repositories, pretrained assets, PDFs, figures and datasets for:

- upstream URL and commit;
- license file;
- redistribution permission;
- local modifications;
- attribution requirements.

De-track unlicensed copied weights/data/assets and retain a reproducible download/provenance manifest instead. Do not claim that “publicly downloadable” automatically permits redistribution.

Write:

```text
third_party_license_audit.csv
PUBLIC_ASSET_PROVENANCE.md
```

## 7. Architecture figure import

The required figures are:

```text
SRR-v2.png
SRR-v2.5.png
SRR-v3.png
CARE-MMRD.png
CARE-SRR-Cascade.png
MoSAIC.png
CARE-DG.png
CARE-ARC.png
CARE-PRISM.png
CARE-MyoWall-IF.png
CARE-ASE.png
```

Canonical destination:

```text
docs/architecture/figures/
```

Look for the files first in either:

```text
/users/a/e/aereinh/CARE_visual_inbox/
docs/architecture/figures_inbox/
```

For each available image:

1. copy into the canonical destination using the exact filename;
2. verify PNG readability and dimensions;
3. compute SHA256;
4. add a short provenance/role record without claiming authorship beyond what the project supports;
5. update `automation/agent_flow_v3/tasks/care-ase-faithful/VISUAL_SOURCES.json` with the GitHub blob URL, raw URL, SHA256, version and `required=true` where applicable;
6. add `docs/architecture/figures/README.md` with a visual index and thumbnail links.

If one or more figures are absent, complete the entire repository cleanup anyway, leave the Agent-Flow request disabled, and write `MISSING_VISUAL_ASSETS.md` with the exact missing names and destination. Do not invent or regenerate missing figures.

## 8. Validation

After cleanup, require:

- no tracked file violates the new local-only rules;
- `git check-ignore` confirms local backups/config/runtime remain ignored;
- all tracked source/tests/docs referenced by current protocols still exist;
- no secret scanner high-confidence finding remains in the current tree;
- no large checkpoint/NIfTI/Docker archive/submission package remains tracked;
- all public code compiles/tests within available environments;
- Agent-Flow v2 and v3 validators pass;
- GitHub Actions workflows are syntactically valid;
- public README links resolve;
- architecture raw URLs return actual PNG bytes after push;
- `REQUEST.enabled` remains false until the visual smoke and scheduled-task binding are complete.

Write:

```text
cleanup_validation.md
post_cleanup_tracked_inventory.csv
public_release_manifest.md
notification_brief.json
```

## 9. Commit and branch handling

Commit the cleanup on `main` in logically grouped commits, then push `main`.

After pushing:

1. fetch `develop`;
2. if `develop` contains no commits absent from cleaned `main`, fast-forward `develop` to the cleaned main head and push;
3. if `develop` has unique commits, merge `main` into `develop` without force and rerun validation;
4. if the merge conflicts or would modify an active Agent-Flow request, stop with `NEEDS_HUMAN_DEVELOP_SYNC` and do not force.

Do not modify or delete historical Route A/B/C branches in this task. Do not rewrite Git history.

## 10. Final report

The final response and notification must state plainly:

- what was removed from tracking but retained locally;
- what active files were parameterized;
- whether any real secret was found;
- remaining repository size risks;
- licensing issues found;
- which architecture figures were imported or remain missing;
- exact main/develop commit SHAs;
- GitHub Actions status;
- that training, outer access, deployment and uploads were not performed.
