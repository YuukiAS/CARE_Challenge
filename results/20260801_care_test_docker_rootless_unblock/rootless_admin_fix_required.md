# Rootless Docker Admin Fix Required

The current Linux server satisfies the user namespace and `newuidmap`/`newgidmap` binary checks, but it does not assign subordinate uid/gid ranges to user `aereinh`. Rootless Docker's official installer checks these files and prints an admin-side fix pattern; this controller cannot apply it because sudo/system-level edits are not authorized.

Required admin-side condition before this task can continue:

```text
/etc/subuid must contain a current-user or uid row with at least 65536 subordinate IDs.
/etc/subgid must contain a current-user or gid row with at least 65536 subordinate IDs.
```

Observed evidence:

```text
subuid_total: 0
subgid_total: 0
unshare -Ur true: returncode 0
newuidmap: /usr/bin/newuidmap
newgidmap: /usr/bin/newgidmap
selected local Docker data root: /tmp/aereinh/care-rootless-docker-data
```

After the site/admin fix, rerun the same task from W1; do not use sudo inside CARE, do not install a system Docker daemon, and do not substitute Apptainer/Singularity for the required Docker build/load/run/save gates.
