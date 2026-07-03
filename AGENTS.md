# CARE repository — agent instructions

## Codex rule source

Treat this `AGENTS.md` as the repo-level Codex rules source. Do not rely on `.cursor/rules/`, `.cursor/skills/`, `.cursor/plans/`, or Cursor plugins; migrate future rule changes here.

## Plan document governance

CARE Myocardium plan files under `docs/plans/` must follow `docs/plans/care_myocardium_plan_registry_rules.md`. Plan filenames must encode lane, round scope, role/status, and topic, for example `laneA_round03_next_edema_trainable_smoke_execution.md` or `laneB_round03plus_controller_cinemyops_hosted_topology_motion_plan.md`.

If a user prompt, generated prompt, or prior ChatGPT instruction conflicts with the plan registry or with `TODO.md`—for example by requesting an ambiguous filename, the wrong round, a controller edit for one-off execution, Round5 repo integration before gates pass, or Cine-only validation upload semantics—do **not** silently comply. Point out the specific contradiction and ask the user to decide before creating or renaming the plan. If the user explicitly overrides the rule, record the exception in the plan metadata.

## Skill Source

- Repo-level skills are installed under `.agents/skills/` from `/overflow/htzhu/mingcheng_new/AI_Skills_Collection/skills`.
- The canonical upstream source remains `/overflow/htzhu/mingcheng_new/AI_Skills_Collection/skills`; when refreshing repo-local skills, replace duplicates with copies from that collection.
- This repository should install the medical imaging skill set from `AI_Skills_Collection/skills/domain/medical-imaging`.
- Do not add `.cursor/skills` or Cursor plugin copies in this repository.

## Reference papers

Third-party papers for consultation live under **`literature/`** (PDFs, etc.). Use them when explaining methods, citations, or baseline details if copies exist there.

## Compute resources

The usual working environment is a compute node. The user also has access to the **`htzhulab`** partition; when CPU-only execution would be slow, use temporary GPU jobs there via `sbatch`, `srun`, or similar Slurm commands instead of letting long CPU runs crawl.

For CARE model work, default to the lab partition first. If queue inspection suggests a materially long wait on `htzhulab`, school GPU partitions may be used as fallbacks. The priority order is:

1. `htzhulab` — preferred/default for CARE jobs.
2. `a100-gpu` — school A100 partition; use only when `htzhulab` is expected to wait too long.
3. `volta-gpu` — school V100 partition; use after `a100-gpu`.

Current Slurm-visible school GPU partitions include:

- `a100-gpu`: `gpu:nvidia_a100-pcie-40gb`
- `volta-gpu`: `gpu:tesla_v100-sxm2-16gb`
- Other visible GPU partitions such as `l40-gpu`, `gpu` (GTX 1080), and `webportal_gpu` are not part of the default CARE fallback order; use them only if the user explicitly asks or the job requirements clearly fit them better.

Before switching away from `htzhulab`, check queue state with commands such as:

```bash
squeue -p htzhulab
sinfo -o '%P|%a|%l|%D|%t|%G'
```

Do **not** switch partitions for short waits or routine pending jobs. Switch only when `htzhulab` is full and the expected wait is long relative to the planned job budget. When switching to school partitions, keep the same logging style, but use the partition-specific Slurm headers below. Do not omit `--qos`: school GPU partitions may reject jobs that inherit an incompatible default QOS. The safe default QOS for CARE fallback jobs is `gpu_access`.

When adding Slurm entrypoints under `jobs/`, mirror the existing header/logging style. Default CARE/lab jobs should use `htzhulab`:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
```

For the school A100 fallback, use this directly usable header:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access
```

Notes for `a100-gpu`: `scontrol show partition a100-gpu` reports `AllowQos=gpu_access,gpu_access_plus`, `MaxTime=6-00:00:00`, nodes `g[141601-141608]`, and `gres/gpu:nvidia_a100-pcie-40gb`. Prefer `gpu_access`; use `gpu_access_plus` only when the user explicitly asks or there is a known reason to request that QOS.

For the school V100 fallback, use this directly usable header:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:tesla_v100-sxm2-16gb:1
#SBATCH --partition=volta-gpu
#SBATCH --qos=gpu_access
```

Notes for `volta-gpu`: `scontrol show partition volta-gpu` reports `AllowQos=gpu_access,hp_volta_gpu,gpu_access_plus`, `MaxTime=11-00:00:00`, nodes `g[0301-0316]`, and `gres/gpu:tesla_v100-sxm2-16gb`. Prefer `gpu_access`; use `gpu_access_plus` or `hp_volta_gpu` only when the user explicitly asks or there is a known reason to request that QOS.

Inside the script, create a timestamped log and tee stdout/stderr there:

```bash
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/<ShortJobName>_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
```

Use filenames like `logs/CineMyoPS_44291121_20260418_111101.log`. Avoid Slurm `%x_%j.out` files unless diagnosing scheduler startup failures.

## Model performance questions

When asked about **model performance** (metrics, Dice, fold CV results):

1. Verify whether **all folds** (usually 0–4) completed using logs and/or `validation/summary.json` (or each model’s metric outputs).
2. If incomplete: state missing folds and report partial results with a clear caveat.
3. If complete: report using the **same document structure and Markdown tables** as `results/metrics/nnUNet.md` (Setup table → label semantics → metric paths → per-dataset fold-wise Mean Val Dice → per-class Dice with Fold0–Fold4 + mean column → optional foreground_mean note → optional log references).

Mirror this layout for non–nnU-Net models; answer in **Simplified Chinese** with English for paths/names as needed.

## Iterative model-improvement runs

For CARE model-improvement work, use short, attributable experiment rounds instead of long speculative training runs.

- Default single training/evaluation job walltime is **8 hours or less**. If an existing Slurm script requests more time, create or use a budgeted entrypoint for the current round.
- Do **not** use very long runs such as 1000/2000 epochs to compensate for weak results. Prefer max-runtime guards, max-epoch caps, validation-based early stopping, and explicit best-checkpoint selection.
- Each round should test one main hypothesis: for example modality dropout, label/remap repair, scar-positive sampling, class-weight tuning, Stage1 prior alignment, or export/cache isolation. Avoid bundling several unrelated changes into one run unless a blocker forces it.
- Start with fold 0 or a small protocol validation loop. Expand to folds 1–4 only after predictions are non-empty, label semantics are verified, cache isolation is verified, and the target leaderboard metric improves or the change fixes a proven pipeline bug.
- Record each round in the relevant file under `results/experiments/*_iteration_log.md`: code changes, command/env vars, fold, walltime, actual epochs, checkpoint used/exported, stop reason, and target metrics before/after.
- Do not silently reuse stale prediction caches. Checkpoint-specific or config-specific prediction and metric directories are required when comparing variants.
- For MyoPS models, optimize and report `myops_scar` and `myops_edema`; for U-MyoPS edema analysis, also report all-cases, GT-positive-only, and T2-present subsets when possible. For CineMyoPS, report both the local `class_1` myocardium proxy and `class_3` scar sanity metric until the hosted `myocardium_cinemyops` metric is calibrated by submission.
- Continue small improvement rounds without asking the user after every run unless there is a decision about data compliance, label definitions, official submission strategy, external credentials, or materially longer compute.

## CARE2026 validation leaderboard

When asked for the latest CARE2026 validation/leaderboard/reference scores, first run:

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

Then answer from the generated latest files under **`results/leaderboard/`**, especially:

- `results/leaderboard/care2026_myocardium_latest.json`
- `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`
- `results/leaderboard/care2026_myocardium_myops_edema_latest.csv`
- `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv`

If the fetch fails because network access is unavailable or the website/API changed, state that clearly and fall back to the most recent existing `*_latest` files with a timestamp caveat.

For CARE2026 challenge interpretation and optimization, focus only on the three leaderboard tasks/metrics:

- `myops_scar`
- `myops_edema`
- `myocardium_cinemyops`

Do **not** treat myocardium, LV_blood, foreground_mean, or other mean/aggregate values as primary objectives. They may be reported as sanity checks when useful, but the main conclusions and repair plans should target the three leaderboard metrics above.

## CARE2026 validation submission packaging

Validation raw data should live under:

- `data/CARE_Challenge/MyoPS_val`
- `data/CARE_Challenge/CineMyoPS_val`

Use `scripts/submission/prepare_care_myocardium_validation.py` as the single entrypoint for validation submissions. One `CARE-Myocardium-OrganAgent.zip` upload contains both `MyoPS/` and `CineMyoPS/`, consumes one validation submission attempt, and returns the three hosted metrics (`myops_scar`, `myops_edema`, `myocardium_cinemyops`) together. Do not plan separate uploads for those three metrics; use per-metric interpretation after the single package is evaluated.

The script writes intermediate inputs/predictions under:

- `results/submissions/care_myocardium_validation/workspaces/<timestamp>__<model_combo_or_run_label>/`

and writes upload-ready packages under:

- `results/submissions/care_myocardium_validation/upload_ready/<timestamp>__<model_combo_or_run_label>/CARE-Myocardium-OrganAgent.zip`
- `results/submissions/care_myocardium_validation/upload_ready/<timestamp>__<model_combo_or_run_label>/manifest.json`

The upload zip filename intentionally has **no timestamp**, because the official example is `CARE-Myocardium-TeamName.zip`. Keep the timestamp at the **front** of the parent folder for chronological sorting and auditability.

Submission organization rule:

- Future upload-ready directory names must be timestamp-first: `<YYYYMMDD_HHMMSS>__<short_descriptive_run_label>`.
- Keep `upload_ready/README.md` updated when manually creating a package outside `scripts/submission/prepare_care_myocardium_validation.py`.
- Keep `upload_ready/` flat: do not add a duplicate chronological symlink layer such as `by_time/`.
- Rename legacy package directories in place to timestamp-first names when cleaning this folder, and then update affected manifests/notes.
- Mark the current best manual-submission candidate in `upload_ready/README.md`; avoid extra pointer directories or symlinks unless the user explicitly requests them.

To prepare the current default nnU-Net 5-fold validation upload zip, use:

```bash
sbatch jobs/submission/prepare_care_myocardium_validation.sh
```

For a local/debug run, use:

```bash
./envs/env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --team-name OrganAgent \
  --submission-model nnUNet \
  --folds 0 1 2 3 4 \
  --checkpoint checkpoint_best.pth
```

Convenience model selection:

- `--submission-model nnUNet`: use nnU-Net for both MyoPS and CineMyoPS.
- `--submission-model MyoPS-Net` or `--submission-model MyoPS`: use MyoPS-Net for the MyoPS side and nnU-Net for the CineMyoPS side.
- `--submission-model CineMyoPS`: use nnU-Net for the MyoPS side and CineMyoPS for the CineMyoPS side.
- `--submission-model U-MyoPS`: only valid when `--myops-pred-dir` points to compact-label U-MyoPS validation predictions; the current repo has protocol fold export for U-MyoPS but not a full validation Stage1→Stage2 inference pipeline.
- `--myops-model ... --cine-model ...`: explicit hybrid combination, for example `--myops-model MyoPS-Net --cine-model CineMyoPS`.

The script converts compact model labels back to CARE raw labels (`200`, `500`, `600`, `1220`, `2221` as applicable). If a prediction has no pathology label at all, it adds a one-voxel `2221` format fallback and records the case in the manifest, because the official validator rejects predictions missing scar/pathology labels.

The official Myocardium validation zip layout is documented at `https://zmic.org.cn/care_2026/valid_submission/`: top-level `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` and `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`.

Default inference policy for the current nnU-Net baseline is a 5-fold ensemble (`fold_0`-`fold_4`) using `checkpoint_best.pth`, because all five folds exist for both Dataset501 and Dataset502. Run it on `htzhulab` GPU by default; use a single best fold only for quick experiments or if ensemble inference is too slow.

<!-- AI_SKILLS_COLLECTION_START -->
# AI Skills Collection

Installed: `2026-06-19T15:42:51+00:00`
Target: `repo`
Install mode: `mixed:domain:medical-imaging+domain:cmr`
Project skills: `.agents/skills/`
Central collection: `/overflow/htzhu/mingcheng_new/AI_Skills_Collection`

When a task matches an installed skill, read that skill's `SKILL.md` before acting. Keep progressive disclosure: load `references/` only when the skill says they are relevant.

## Skill Routing

### cmr
- `cardiacnexus-docs-markdoc`: Project-specific guidance for the CardiacNexus documentation site in docs/. Use when editing Markdoc pages, navigation, metadata, Next.js static export settings, phenotype documentation, or preparing the site for stat... Path: `.agents/skills/projects-cmr-cardiacnexus-docs-markdoc/SKILL.md`
- `cardiacnexus-feature-contracts`: Project-specific guidance for CardiacNexus phenotype outputs. Use when adding, renaming, validating, aggregating, or documenting CSV/NPZ/QC outputs, units, column schemas, cross-modality features, or downstream-facing... Path: `.agents/skills/projects-cmr-cardiacnexus-feature-contracts/SKILL.md`
- `cardiacnexus-pipeline-refactor`: Project-specific guidance for refactoring the CardiacNexus UKB CMR pipeline. Use when touching config.py, step1-4 orchestration, Slurm script generation, segmentation wrappers, feature extraction boundaries, packaging... Path: `.agents/skills/projects-cmr-cardiacnexus-pipeline-refactor/SKILL.md`
- `cardiacnexus-strain-registration`: Project-specific guidance for CardiacNexus strain and registration refactors. Use when editing eval_strain_lax.py, eval_strain_sax.py, cardiac_utils motion/contour code, MIRTK integrations, or when introducing ANTsPy... Path: `.agents/skills/projects-cmr-cardiacnexus-strain-registration/SKILL.md`

### medical-imaging
- `medical-imaging-classical-features`: Use when enforcing reproducible preprocessing, registration baselines, radiomics protocols, or DICOM SEG/SR provenance in CardiacNexus. Path: `.agents/skills/domains-medical-imaging-medical-imaging-classical-features/SKILL.md`
- `medical-imaging-deep-learning`: Aligns with CardiacNexus MONAI-first refactor and high-risk registration/strain awareness. Path: `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `medical-imaging-terminology-measurement`: Use medical imaging terminology and measurement conventions with source checks, modality-specific caveats, structured reporting boundaries, and uncertainty language. Path: `.agents/skills/domains-medical-imaging-medical-imaging-terminology-measurement/SKILL.md`
- `pathml`: Full-featured computational pathology toolkit. Use for advanced WSI analysis including multiplexed immunofluorescence (CODEX, Vectra), nucleus segmentation, tissue graph construction, and ML model training on patholog... Path: `.agents/skills/domains-medical-imaging-pathml/SKILL.md`
- `pydicom`: Python library for working with DICOM (Digital Imaging and Communications in Medicine) files. Applies to tasks involving medical image analysis, PACS systems, radiology workflows, and healthcare imaging applications. Path: `.agents/skills/domains-medical-imaging-pydicom/SKILL.md`

## Skill Maintenance

- Update command: `python3 /overflow/htzhu/mingcheng_new/AI_Skills_Collection/scripts/skills.py install --target repo --mode symlink --skill domain/medical-imaging/medical-imaging-classical-features --skill domain/medical-imaging/medical-imaging-deep-learning --skill domain/medical-imaging/medical-imaging-terminology-measurement --skill domain/medical-imaging/pathml --skill domain/medical-imaging/pydicom --skill project/cmr/cardiacnexus-docs-markdoc --skill project/cmr/cardiacnexus-feature-contracts --skill project/cmr/cardiacnexus-pipeline-refactor --skill project/cmr/cardiacnexus-strain-registration --write-agents-md`
- Managed manifest: `.agents/skills/.ai-skills-collection-manifest.json`
- The installer only manages paths recorded in that manifest.
- User-created skills outside the manifest are never pruned.
<!-- AI_SKILLS_COLLECTION_END -->

<!-- ai-bridge-kit:start -->
# Handoff Protocol

本项目采用 `prompts/` handoff 协议，用于 ChatGPT 和 Codex 之间的文件化交接。

## 默认入口

- `prompts/AGENT_RULES.md`：长期执行规则。
- `prompts/CHATGPT_RULES.md`：ChatGPT 通过 GitHub MCP 或仓库工具写 task、note、review 时应读取的规则。
- `prompts/tasks/<task_key>.md`：唯一默认任务入口；`task_key` 使用 `<id>_<short_slug>`，short slug 控制在 1-3 个词内。
- `results/<task_key>/result.md`：Codex 的执行报告和证据索引。
- `results/<task_key>/review.md`：ChatGPT 的复盘位置。
- `docs/notes/`：参考笔记、方案分析、会议记录和讨论沉淀，不是默认任务入口。
- `results/<task_key>/`：Codex、脚本或实验生成的文件型产物目录；目录名必须与 task 文件名完全一致。
- `docs/wiki/`：长期研究知识库，不是默认任务入口。

## Result Publication Boundary

Generated `results/20??????_*` handoff/controller run directories are
data-derived local evidence packages. They are ignored by default and must not be
published wholesale.

When GPT needs repository-visible context for deciding the next task, publish
only the smallest reviewed Markdown decision packet. Prefer the controller
`controller_report.md` and `execution_plan.md`, plus each relevant subtask's
`result.md` and `review.md`. Do not publish CSV tables, prediction outputs,
checkpoints, logs, environment dumps, command transcripts, subagent prompts, or
full result manifests unless the user explicitly approves that narrower
disclosure after review.

Because the result directories are ignored, any approved decision packet should
be added with explicit `git add -f <file>` paths. Do not change `.gitignore` to
unignore an entire generated result tree.

## Codex 行为规则

- Codex 开始任务前应读取 `prompts/AGENT_RULES.md` 和指定的 `prompts/tasks/<task_key>.md`。
- Codex 必须遵守 task frontmatter、允许动作、禁止动作和停止条件。
- Codex 完成后必须写 `results/<task_key>/result.md`；如果生成日志、表格、图、导出包、长报告或中间输出，写入同名 `results/<task_key>/`，写 `results/<task_key>/MANIFEST.md`，并在 result 中列出产物清单。
- Codex 不应主动执行 `docs/notes/` 或 `docs/wiki/` 中的内容，除非任务单显式引用某篇 note 或 wiki 页面作为背景材料。
- 如果任务需要联网、上传、删除数据、运行昂贵命令或修改高风险配置，但 task 没有授权，Codex 必须停止并在 result 中请求人工批准。

## ChatGPT / GitHub MCP 行为规则

- ChatGPT 通过 GitHub MCP 处理本仓库时，应先读取 `AGENTS.md` 和 `prompts/CHATGPT_RULES.md`。
- 需要 Codex 执行的内容必须写成 `prompts/tasks/<task_key>.md`。
- 只作参考的研究分析、方案比较、会议记录和复盘应写到 `docs/notes/`。
- 执行产生的文件型产物应写到同名 `results/<task_key>/`，并用 `results/<task_key>/MANIFEST.md` 反向链接 task/result/review；不要塞进 `prompts/tasks/` 或 `docs/notes/`。
- 有长期复用价值的论文摘要、报告摘要、概念、对比、gap 和综合讨论应写到 `docs/wiki/`。
- ChatGPT 不应把 issue、PR description 或聊天正文当作 Codex 的唯一任务来源。
<!-- ai-bridge-kit:end -->
