# Cleanup Validation

本轮完成的是公共仓库卫生清理和架构图导入，没有启用 CARE-ASE Agent-Flow REQUEST，没有训练，没有访问 outer，没有构建或上传 Docker，也没有合并实验实现。

| Check | Result |
| --- | --- |
| Pre-clean tracked files | 8281 |
| Post-clean tracked files | 8055 |
| Detracked files | 226 |
| Detracked bytes | 441478172 |
| Tracked-but-ignored conflicts after cleanup | 5333 |
| Tracked local-only binary/log/archive/auth extensions after cleanup | 0 |
| Secret/private-key blocker findings | 0 |
| Architecture figures imported | 11 |
| Architecture figures missing | 0 |
| Remaining large tracked files rows | 918 |
| Server-local backup root | `/users/a/e/aereinh/.public-repo-cleanup/20260805_CARE` |

The remaining tracked-but-ignored entries are recorded in `post_cleanup_tracked_ignored_conflicts.csv`; they are dominated by legacy lightweight results and archive-policy rules, not by the newly de-tracked local-only binary/log/archive/auth classes. Validation artifacts: `post_cleanup_tracked_inventory.csv`, `post_cleanup_tracked_ignored_conflicts.csv`, `post_cleanup_large_current_files.csv`, `secret_scan_summary.md`, `secret_scan_classification.csv`, `detracking_manifest.csv`.
