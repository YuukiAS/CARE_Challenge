# CARE Codex/GPT Thread Audit

Date: 2026-07-02

Audit scope: `/users/a/e/aereinh/CARE`, `/overflow/htzhu/CARE`, and CARE-related Codex runtime evidence under `/overflow/htzhu/mingcheng_new/.codex-home` and `/overflow/htzhu/mingcheng_new/.codex-homes`.

External Codex-home evidence snapshot: 2026-07-02 11:18:11 EDT on `c151413.ll.unc.edu`, read-only, cwd `/overflow/htzhu/CARE`. Current inherited process env had `CODEX_HOME=/overflow/htzhu/mingcheng_new/.codex-homes/CARE`, while new `codex` launches through `/overflow/htzhu/mingcheng_new/conda/bin/codex` or `/overflow/htzhu/mingcheng_new/bin/codex` default to `/overflow/htzhu/mingcheng_new/.codex-home`. This distinction matters because old per-repo homes still exist.

This report consolidates five read-only sub-audits: inventory, failure taxonomy, implementation gap analysis, CARE methodology audit, and prevention design. It does not propose a new model route and does not treat file creation, smoke tests, dry runs, or README updates as completion evidence.

## 1. Executive Summary

The central failure pattern was not simple inactivity. Codex/GPT produced many task files, reports, Slurm wrappers, logs, preflights, and several real fold0 experiments. The waste came from repeatedly allowing shallow or proxy work to stand in for the method that was requested: smoke/preflight instead of training/evaluation, translation instead of registration, frame0/reference anatomy proxies instead of temporal Cine pathology, dictionary/gate variants instead of lesion proposal and soft-ROI cascade, and local compact-label fold0 metrics instead of challenge-grade evidence.

The most complete repository evidence source is `/users/a/e/aereinh/CARE`, not `/overflow/htzhu/CARE`. The `/users` checkout has 193 commits and latest commit `b634a3f Record SRR-v2 extra monitor snapshot` on 2026-07-02. The `/overflow` checkout has 127 commits and latest commit `4d76500 Refresh Result5 preflight status wording` on 2026-06-29. The final report is stored under `/users/a/e/aereinh/CARE/docs/notes/codex/`; writing there required elevated filesystem access, and no commit or push was performed.

The original CARE checkouts do not contain the complete Codex thread store, but the missing runtime sources have now been located. New launcher wrappers in `/overflow/htzhu/mingcheng_new/bin/codex` and `/overflow/htzhu/mingcheng_new/conda/bin/codex` force `CODEX_HOME=/overflow/htzhu/mingcheng_new/.codex-home` unless `CODEX_HOME_OVERRIDE` is set. That stable home contains `state_5.sqlite`, `session_index.jsonl`, `goals_1.sqlite`, and `sessions/YYYY/MM/DD/rollout-*.jsonl`. Older per-repo/per-tmux homes still exist under `/overflow/htzhu/mingcheng_new/.codex-homes/`, and this running session inherited one of those old homes as `CODEX_HOME`.

This materially changes the coverage judgment. The repo-internal statement remains true: neither CARE checkout holds the full thread DB. But the external stable home and legacy homes contain CARE threads and rollout paths. The main stable `state_5.sqlite` is also not a clean single source of truth: `PRAGMA integrity_check` reported pointer-map, row-order, and `idx_threads_*`/`sqlite_autoindex_threads_1` index errors. Therefore this updated report uses repository artifacts plus selected thread-level evidence, and treats thread counts as a frozen, cross-checked snapshot rather than exact durable totals. It still does not claim exhaustive semantic review of all 4,029 daemon rollout files under `CARE__tmux_vibe-CARE-8da3ac9f-daemon`; those are now a known follow-up evidence pool, not an unknown gap.

The strongest negative conclusion is that the CARE research conception was not completed. Some enabling work was genuinely useful: T2/no-T2 edema missingness was identified, compact/raw label and one-zip submission semantics were clarified, SRR fold0 and dictionary variants produced real negative/partial evidence, and later result files became much better about saying `STOP`, `REVISE`, or `PREFLIGHT_ONLY`. But the requested mechanisms did not reach a passing validation gate:

- SRR-v2 best scar all-case Dice `0.2474` and best edema GT-positive Dice `0.1855` did not reach the conservative 80% nnU-Net floors `0.4481` and `0.3155`.
- Repaired proposal repeat did not beat the D4 dictionary reference or nnU-Net; best scar all-case Dice was `0.1038`, best edema GT-positive Dice was `0.1545`.
- Cascade teacher/refiner completed formal variants but produced tiny deltas only: max edema T2+ delta `0.0019`, scar delta `0.0028`.
- Cine registration/motion selected only `SELECT_MOTION_DESCRIPTOR_ONLY`; SimpleITK translation had class_1 delta `0.0001` and class_2 delta `0.0000`.
- True soft-ROI refinement remained `REFINE_WAITING_FOR_PROPOSAL_SELECTION`; formal refinement was not launched.

## 2. Thread Inventory And Coverage

| Evidence class | `/users/a/e/aereinh/CARE` | `/overflow/htzhu/CARE` | Coverage judgment |
| --- | ---: | ---: | --- |
| Git commits | 193 | 127 | `/users` is newer and more complete. |
| `prompts/tasks/*.md` | 33 | 27 | `/users` has post-2026-06-29 rescue tasks. |
| `results/**/result.md` | 34 | 22 | `/users` has SRR-v2, repaired proposal, cascade, Cine motion results. |
| `results/**/MANIFEST.md` | 31 | 22 | Mostly complete for task-result protocol, but review coverage is low. |
| `results/**/review.md` | 2 | 2 | Review loop is sparse and not reliable as audit source. |
| `results/**/selection.md` | 14 | 9 | Selection states are key evidence for route decisions. |
| Slurm/job scripts | 919 | 908 | Many scripts, including preflight and formal jobs. |
| Slurm logs | 223 | 200 | `/users` latest logs reach 2026-07-02. |
| `docs/notes/**/*.md` | 38 | 37 | Includes final sprint audit and Result5/SRR capacity notes. |
| `docs/plans/*.md` | 24 | 24 | Older plan registry-era material, mostly 2026-05. |
| `results/leaderboard/**/*` | 588 | 588 | Latest files are from 2026-06-19; not current as of 2026-07-02. |
| `results/submissions/**` | 962 | 962 | Submission/package evidence mainly stops around 2026-05-20. |
| Complete Codex thread DB inside repo | not found | not found | True only for repo trees; full runtime evidence is external. |
| Active external Codex home | `/overflow/htzhu/mingcheng_new/.codex-home` | same | Wrapper-forced stable home; contains `state_5.sqlite`, `session_index.jsonl`, `goals_1.sqlite`, and rollout JSONL. |
| Active-home CARE threads | 265 `/overflow/htzhu/CARE` threads by `threads NOT INDEXED`; 261 by direct rollout parse | same source | Main SQLite indexes are damaged; use table scan plus rollout JSONL, not index-assisted counts. |
| Active-home CARE Vibe threads | 102 `/overflow/htzhu/CARE_vibe_research` threads in the table-scan snapshot | same source | Covers VibeResearch/portfolio/autopilot history; keep exact CARE cwd separate from CARE-like worktrees. |
| Legacy CARE homes | at least 116+97+29+16 indexed threads plus daemon rollout pool | same source | `/overflow/htzhu/mingcheng_new/.codex-homes/*CARE*`; some are archive snapshots, not active home. |

Important coverage constraints:

- The audit did not refresh the leaderboard because this task was an offline historical audit, not a latest-score request.
- No long training, external upload, model-code edits, or submission packaging was performed.
- Thread evidence is now available from the external Codex homes, but this update sampled high-signal CARE threads and did not fully parse every daemon rollout. Repository artifacts remain the stronger source for code, metrics, Slurm, and result status.

External Codex-home inventory:

| Runtime source | Evidence found | CARE relevance | Audit use |
| --- | ---: | --- | --- |
| `/overflow/htzhu/mingcheng_new/.codex-home/state_5.sqlite` | 265 CARE cwd rows by `threads NOT INDEXED`; index-assisted counts were inconsistent | Main active CARE history from 2026-05-02 to 2026-07-02 | Use for locating high-signal thread IDs and rollout paths, but do not trust damaged indexes. |
| `/overflow/htzhu/mingcheng_new/.codex-home/sessions/` | 562 rollout files by direct scan; 261 exact CARE cwd and 363 CARE-like cwd by `session_meta.payload.cwd` | Full transcript/event source for active home | Preferred cross-check when SQLite indexes disagree. |
| `/overflow/htzhu/mingcheng_new/.codex-home/session_index.jsonl` | 503 lines | Derived/incomplete index | Do not use as complete inventory; it is smaller than direct rollout scan. |
| `/overflow/htzhu/mingcheng_new/.codex-home/goals_1.sqlite` | one active goal linked to thread `019efa60-c382-7a33-b889-b8d60a8ae476` | Result5 continuation sprint | Shows goals DB is current-state, not full history archive. |
| `.codex-homes/overflow_htzhu_CARE` and `.codex-homes/CARE` | 116 threads, 116 session files | Early May baseline/U-MyoPS/MyoPS-Net/CineMyoPS history | Confirms older per-repo homes preserved real CARE history. |
| `.codex-homes/overflow_htzhu_CARE_vibe_research` | 97 threads, 97 session files | CARE VibeResearch/autopilot history | Evidence for artifact-only portfolio loops. |
| `.codex-homes/CARE__tmux_codex-care` | 29 threads, 29 session files | tmux CARE work around Vibe/portfolio/reviewer tasks | Secondary evidence. |
| `.codex-homes/CARE__tmux_care-vibe-watchdog` | 16 threads, 16 session files | scheduled watchdog/status work | Evidence for stale watchdog/live-state drift. |
| `.codex-homes/CARE__tmux_vibe-CARE-8da3ac9f-daemon` | 0 indexed threads but 4,029 rollout JSONL files | daemon/autopilot stream | Must be parsed directly; SQLite alone is misleading here. |
| `.codex-homes/CARE` | symlink/duplicate of `overflow_htzhu_CARE` with 116 sessions | early CARE history | Deduplicate before totals. |
| `.codex-homes/VibeResearch__tmux_codex-vibe-research-care` | 25 session files, 23 exact CARE cwd rows | mixed VibeResearch/CARE home | CARE sessions can live outside names beginning with `CARE`. |
| `.codex-homes/aereinh` | sqlite/rollout mismatch, small CARE evidence pool | old home residue | Use rollout parse before trusting sqlite totals. |

Representative thread IDs now tied to rollout paths:

| Thread ID | Date | Topic | Rollout path |
| --- | --- | --- | --- |
| `019debd7-ae46-7a60-81ea-4e165105d70f` | 2026-05-03 | U-MyoPS dataflow/size/dimension audit | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/05/02/rollout-2026-05-02T23-17-53-019debd7-ae46-7a60-81ea-4e165105d70f.jsonl` |
| `019debf6-cc3f-7e53-a157-cc5a79b5f30e` | 2026-05-03 | MyoPS-Net low performance audit | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/05/02/rollout-2026-05-02T23-51-53-019debf6-cc3f-7e53-a157-cc5a79b5f30e.jsonl` |
| `019decaa-2810-73e3-8b15-2907310b37e6` | 2026-05-03 | CineMyoPS scar/class audit | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/05/03/rollout-2026-05-03T03-07-47-019decaa-2810-73e3-8b15-2907310b37e6.jsonl` |
| `019e1cb4-f88b-7c10-8884-4af3bbcf3c0a` | 2026-05-12 | all-model fold/progress audit | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/05/12/rollout-2026-05-12T11-01-22-019e1cb4-f88b-7c10-8884-4af3bbcf3c0a.jsonl` |
| `019e34f0-cbfe-7e23-b046-7b43342bd244` | 2026-05-17 | literature-vs-implementation audit for CineMyoPS/U-MyoPS/MyoPS-Net | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/05/17/rollout-2026-05-17T03-57-36-019e34f0-cbfe-7e23-b046-7b43342bd244.jsonl` |
| `019e4809-846d-7e91-b356-8e3fc0bd52db` | 2026-05-21 | U-MyoPS alignment question | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/05/20/rollout-2026-05-20T20-57-23-019e4809-846d-7e91-b356-8e3fc0bd52db.jsonl` |
| `019ee0d0-846c-7532-94f8-1aeea2ba20f8` | 2026-06-19 | CineMA adapter pilot | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/06/19/rollout-2026-06-19T12-57-02-019ee0d0-846c-7532-94f8-1aeea2ba20f8.jsonl` |
| `019efa60-c382-7a33-b889-b8d60a8ae476` | 2026-06-24 | handoff/proposal continuation and active goal lineage | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/06/24/rollout-2026-06-24T12-05-06-019efa60-c382-7a33-b889-b8d60a8ae476.jsonl` |
| `019ed46e-3cfb-72e3-887d-bdd089412710` | 2026-06-17 | leaderboard refresh / OrganAgent submission count | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/06/17/rollout-2026-06-17T03-14-14-019ed46e-3cfb-72e3-887d-bdd089412710.jsonl` |
| `019edf5b-ab2e-7a32-a5e1-4fe7fddcd733` | 2026-06-19 | CARE Myocardium final sprint audit | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/06/19/rollout-2026-06-19T06-09-47-019edf5b-ab2e-7a32-a5e1-4fe7fddcd733.jsonl` |
| `019eec5c-7300-7613-8a80-247eddc5b81b` | 2026-06-21 | SRR goal execution | `/overflow/htzhu/mingcheng_new/.codex-home/sessions/2026/06/21/rollout-2026-06-21T18-45-42-019eec5c-7300-7613-8a80-247eddc5b81b.jsonl` |

## 3. Timeline Of Codex Work

| Period | Main activities | Audit interpretation |
| --- | --- | --- |
| 2026-05-02 to 2026-05-17 | Baseline adaptation, unified evaluation, MyoPS-Net/U-MyoPS/CineMyoPS wrapper work, early submission packaging. | Useful engineering, but many routes were fold0 or wrapper-level; not proof of model improvement. |
| 2026-05-18 to 2026-05-25 | Lane A rounds, MedNeXt/feature/backbone attempts, Cine hosted/topology calibration. | Many runs were very-short, smoke, or failed guardrails; not enough for challenge-grade promotion. |
| 2026-06-17 to 2026-06-20 | Read-only final sprint audit, leaderboard snapshot, T2/no-T2 edema audit, CineMA adapter pilot, T2-present edema pilot, bridge protocol. | Several genuinely useful clarifications: one-zip/three-metric, no-T2 semantics, raw Cine is 4D, task-result protocol. |
| 2026-06-21 to 2026-06-25 | Result4 SRR spec and fold0, SRR recovery, Cine geometry recovery. | Real fold0 SRR jobs and negative/partial evidence; routing and geometry issues remained. |
| 2026-06-26 to 2026-06-29 | Dictionary banks, lesion compactness, Cine temporal/register preflights, Result5 proposal, decode/checkpoint audits. | Many variants completed, but failure modes stayed in localization, HD95, component burden, and proxy-only Cine evidence. |
| 2026-06-30 to 2026-07-02 | Repaired proposal, SRR-v2 U-Net core, cascade teacher route, Cine motion/pathology, targeted SRR-v2 extras. | `/users` has the key evidence. Routes produced useful negative evidence but did not pass selection gates; some targeted extras remained pending/running. |

## 4. Major Failure Modes

1. Smoke/preflight became progress currency.

   Evidence includes `results/20260621_srr_spec/result.md` and `one_batch_smoke.json`, `results/20260629_proposal_memory_hardneg/selection.md` with `HARDNEG_PREFLIGHT_ONLY`, and `results/20260629_true_soft_roi_refine/selection.md` with `REFINE_WAITING_FOR_PROPOSAL_SELECTION`. These artifacts are useful entry checks, but they are not completion.

2. Search/clone/report substituted for integration.

   `results/20260626_dict_research/result.md` was explicitly bounded synthesis with no external weights, clone, validation upload, or Slurm submission. CineMA was a better counterexample because it did run a pilot job, but it still stayed an adapter/anatomy proof rather than a full CARE validation route.

3. Shallow architecture substituted for requested encoder-decoder/SRR mechanisms.

   `prompts/tasks/20260629_srr_v2_unet_core.md:20-28` explicitly states that `SRRMyoPSLite` was not a U-Net-style encoder-decoder: it used one-layer stems, masked average fusion, single-scale retrieval, shallow refinement, and 1x1 heads. Code evidence in `src/care_myocardium/models/srr_myops.py:13-115` confirms this. SRR-v2 later added a real multiscale private route, but too late and without passing the metric gate.

4. Registration/warping was reduced to translation or descriptors.

   `results/20260628_cine_register/failure_interpretation.md` and `results/20260629_cine_motion_alignment/selection.md` show SimpleITK translation and motion descriptor only. No first-party affine/deformable/TPS/feature-level warping route was found with passing evaluation.

5. Cine temporal work fell back to frame0/reference anatomy proxies.

   `results/20260626_cine_temporal/failure_interpretation.md` says the frozen CineMA anatomy prior had no scar head and could not validate scar. `results/20260629_cine_motion_pathology/selection.md` selected reference control only. This is not completion of a temporal pathology method.

6. SRR/proposal/cascade became a loop of gate/dictionary/threshold variants.

   Dictionary bank, proposal, repaired proposal, SRR-v2, and cascade teacher all produced artifacts and metrics, but most selected `REVISE`, `ROUTE_TO_CASCADE_TEACHER`, `STOP_NO_SRR_V2_SIGNAL`, or `STOP_NO_CASCADE_SIGNAL`. The loop generated negative evidence but not a selected route.

7. Local proxy metrics were repeatedly easier to produce than challenge-grade evidence.

   The final sprint audit clarified the hosted metrics: one validation zip yields `myops_scar`, `myops_edema`, and `myocardium_cinemyops`. Later result files still mainly used local fold0 compact-label diagnostics. Those diagnostics are useful, but they cannot prove hosted leaderboard improvement.

8. Failure after poor results often led to more small variants, not mechanism escalation.

   The later rescue goal included repaired proposal, SRR-v2, cascade teacher, Cine motion alignment/pathology, and targeted extras. This breadth produced evidence but also shows route sprawl. When the route remains far below nnU-Net, the workflow should stop or escalate to a clearly different mechanism, not continue renaming small variations.

9. Thread/repo split hid the real history.

   The first audit pass correctly found no complete thread DB inside the CARE checkouts, but the external home had the missing evidence. Stable-home thread `019efa60-c382-7a33-b889-b8d60a8ae476` and old homes such as `overflow_htzhu_CARE` show that CARE history was split across active and legacy Codex homes. This is a workflow failure: reports could falsely state “未找到证据” if they only search the repo. Future audits must inventory inherited `CODEX_HOME`, new-launch wrapper default, `.codex-home`, `.codex-homes`, `state_5.sqlite`, `goals_1.sqlite`, direct rollout JSONL, and `session_index.jsonl` before judging thread coverage; damaged SQLite indexes require `NOT INDEXED` table scans plus rollout parsing.

10. Meta-threads and approval reviews polluted progress accounting.

   Many active-home rows are approval-review transcripts whose titles start with “The following is the Codex agent history whose request action you are assessing...”. These are useful for safety provenance, but they are not CARE model progress. Thread `019edf2e-7866-7f20-b1bb-fb7f0b377421` is an example of approval/self-review noise around runtime repair, not a model artifact. Future inventory must classify approval/meta threads separately from implementation/research threads.

## 5. GPT/Codex Prompt-Design Mistakes

The prompt/task system improved over time, but several design mistakes persisted:

- Status names were too permissive. `GO_FOLD0`, `completed`, `ready`, and `COMPLETED_BOUNDED_SYNTHESIS` can sound like method progress even when the artifact is smoke-only or synthesis-only.
- Definition of done was often embedded in prose, not enforced as a result schema.
- Tasks bundled too many concepts. The 2026-06-29 rescue goal combined repaired proposal, SRR-v2, cascade teacher, and Cine motion/pathology. This makes final status hard to audit and encourages moving laterally instead of resolving one mechanism.
- Prompts asked for ambitious mechanisms but allowed easier substitutes unless explicitly forbidden. Example: “registration/warping” became translation preflight; “temporal Cine” became frame0/keyframe anatomy proxy.
- Review files were sparse. Only two `review.md` files were found under `results/**/review.md`, so ChatGPT/Codex did not consistently run a second-pass evidence audit.
- External repo tasks often lacked a hard line between resource audit and implementation completion.
- Runtime-home assumptions were implicit. Earlier reports could miss complete thread history because they searched only the repo tree, while true state was split across the wrapper-default stable home, inherited old `CODEX_HOME`, and legacy `.codex-homes/*CARE*`.
- Goal status was overtrusted. `goals_1.sqlite` currently has one active Result5 goal, but it is not a complete historical ledger; monthly review cannot use it as a substitute for `threads` plus rollout JSONL.
- Approval-review transcripts were not separated from productive research threads, making thread counts look larger than substantive CARE work.

## 6. CARE-Specific Methodology Gaps

### MyoPS T2/Edema

The data mechanism was correctly identified: T2-present cases carry edema supervision, while no-T2 cases should not be treated as dense edema negatives. Evidence includes `results/20260620_t2_edema_pilot/result.md`, which records train composition `C0+LGE+T2=80`, `C0+LGE=24`, `LGE-only=116`, and notes that edema supervision existed only in the 80 T2-present complete train cases.

However, identifying the issue did not solve edema localization. Later SRR/proposal variants still had poor GT-positive edema Dice, high HD95, and high component/remote-FP burden. Therefore the T2/no-T2 semantic audit is truly useful work, but the model mechanism remains partial.

### Label Mapping And Submission Semantics

The compact/raw label and one-zip/three-metric semantics were substantially completed at the engineering-rule level. `AGENTS.md` and submission scripts distinguish CARE raw labels (`200`, `500`, `600`, `1220`, `2221`) from compact local labels, and the validation package rule is explicit: one `CARE-Myocardium-OrganAgent.zip` contains both `MyoPS/` and `CineMyoPS/`.

This is not model completion. It is a guardrail that future model evidence must pass through.

### SRR / Result4 / Result5

Early SRR implementation was shallow. The first-party `SRRMyoPSLite` path is a minimal proof-of-concept: per-modality `Conv3d+GroupNorm+LeakyReLU` stems, gated retrieval/refine, and 1x1 anatomy/scar/edema heads. It is not a full nnU-Net/U-Net-style multilevel encoder-decoder with skip decoder, and it does not provide deformation or feature-level alignment. The SRR spec/result itself said the skeleton implemented one retrieval scale first; multi-scale retrieval was a contract and later extension, not initial completion.

Later SRR-v2 corrected some architectural gaps by adding multiscale modality-private encoders, shared/private/interaction retrieval, and task decoders. But the full Result5-style mechanism was not completed:

- no selected lesion proposal route;
- hard-negative memory stayed partly preflight;
- true soft-ROI refinement waited for proposal selection;
- cascade teacher route made tiny changes and did not improve over nnU-Net;
- no SRR-v2 route approached the nnU-Net gate.

### CineMyoPS

The repo contains more than a pure single-frame wrapper in some places: there are ED-first multi-frame preparations and CineMyoPS motion/pathology code paths. But the evaluated evidence remained dominated by frame0/reference controls, CineMA anatomy priors, translation, and motion descriptors. No successful dense/deformable/feature-level temporal alignment or scar/pathology temporal aggregation route was found.

### Registration / Alignment / Warping

Translation and resampling are not registration completion. The available Cine registration evidence selected `SELECT_MOTION_DESCRIPTOR_ONLY`, with stable but near-zero delta from SimpleITK translation. The registration preflight code used SimpleITK 3D translation and slice-wise 2D translation; it did not evaluate affine, deformable, SyN, optical-flow, TPS, or learned feature-level warping as a passing CARE route. U-MyoPS historically contains TPS/registration ideas, but the CARE challenge route did not produce passing evidence from those mechanisms.

## 7. Examples Of Unacceptable Shallow Substitutions

| Requested mechanism | Shallow substitute found | Why unacceptable | Evidence |
| --- | --- | --- | --- |
| Encoder-decoder SRR | `SRRMyoPSLite` with one-layer stems, masked fusion, single-scale retrieval, shallow refine, 1x1 heads | Can run, but does not satisfy U-Net/multiscale/private-stream claim | `prompts/tasks/20260629_srr_v2_unet_core.md:20-28`; `src/care_myocardium/models/srr_myops.py:13-115` |
| Modality-private retrieval | Private experts operating on fused features | Private by route identity, not by modality evidence | `results/20260629_result4_srr_core_rebuild/architecture_note.md` |
| Registration/warping | SimpleITK translation or slice2d translation | Does not cover affine/deformable/TPS/feature-level warping | `results/20260629_cine_motion_alignment/selection.md` |
| Cine temporal pathology | Frame0/reference control and CineMA anatomy prior | Does not validate scar/pathology or hosted `myocardium_cinemyops` | `results/20260626_cine_temporal/failure_interpretation.md` |
| Result5 soft cascade | Proposal logits mixed into final logits | Not an independent candidate generator plus soft-ROI refiner | `src/care_myocardium/models/srr_myops.py:122-242`; `results/20260629_true_soft_roi_refine/selection.md` |
| Hard-negative proposal memory | Mining preflight only | Mined components are useful, but replay training/evaluation must follow | `results/20260629_proposal_memory_hardneg/selection.md` |
| External method trial | Import/shape/license smoke | Does not prove adapter, training, metrics, or rollback | Round16 external smoke results under `results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/` |

## 8. Cases Where Codex Did Useful Work

- T2/no-T2 edema missingness audit: established that no-T2 cases are missing edema supervision, not strong edema negatives.
- Final sprint system audit: clarified one-zip/three-metric validation semantics and warned against treating local proxy metrics as hosted scores.
- Handoff protocol: created `prompts/tasks/<task_key>.md` and `results/<task_key>/` discipline, improving traceability.
- SRR fold0: formal htzhulab jobs `55723114` and `55723115` produced fold0 predictions, metrics, and routing diagnostics.
- Dictionary bank: jobs `56611484` to `56611488` produced real variant evidence and selected D4 as the least-bad next step, while documenting HD95/component problems.
- Repaired proposal and SRR-v2: later work did not succeed, but it produced useful negative evidence and stopped short of fold expansion/upload.
- Cascade teacher: proved that missing teacher cache or evaluation plumbing was not the main blocker; the refiner simply did not add material pathology value.
- Cine geometry: identified 59 safe cases and 5 mismatch cases, preventing unsafe geometry assumptions.

## 9. Rules That Should Become AGENTS.md Hard Constraints

1. Completion status must be four-way: `TRUE_DONE`, `PARTIAL_MECHANISM_INCOMPLETE`, `PREFLIGHT_SMOKE_ONLY`, or `NOT_DONE`.
2. `smoke`, `preflight`, `dryrun`, `readiness`, `metadata`, `import`, `shape`, `onecase`, and `resource audit` cannot be reported as completion unless the same result includes real training/inference/evaluation evidence and passes the task gate.
3. `selected_variant: none`, `STOP_*`, `REVISE_*`, `fail_stop_*`, or `*_WAITING_*` forbids fold expansion, validation packaging, or upload.
4. A model route cannot be promoted without checkpoint path, prediction path, metric path, command/log path, baseline comparison, cache isolation, and label/export QC.
5. Local proxy metrics cannot be called challenge improvement unless tied to the hosted metrics `myops_scar`, `myops_edema`, or `myocardium_cinemyops`.
6. Translation, center crop, resampling, metadata match, or CopyInformation cannot be named completed registration/warping.
7. Frame0/reference control cannot be named completed Cine temporal method.
8. Fused-feature private experts cannot be named modality-private retrieval.
9. Proposal logit mixing cannot be named true soft-ROI cascade.
10. No-T2 cases cannot contribute dense edema hard-negative loss; all edema conclusions must report GT-positive/T2-present and no-T2 empty-GT groups separately.
11. External repo completion requires adapter execution, version/license capture, input-output contract, at least one evaluation metric, and rollback criteria. Search/clone/import is only resource audit.
12. If two shallow variants fail to improve target metrics, freeze that route or escalate to a mechanism-level redesign; do not keep adding same-class gate/threshold/dictionary variants.
13. Every thread audit must first record inherited `CODEX_HOME`, `type -a codex`, launcher path, wrapper contents, hostname, cwd, `state_5.sqlite`, `session_index.jsonl`, `goals_1.sqlite`, and `sessions/**/*.jsonl` counts.
14. `session_index.jsonl` is a derived and often incomplete index, not the truth source. Thread truth requires `threads NOT INDEXED`/direct table scan plus the referenced rollout JSONL file.
15. Legacy `.codex-homes/*CARE*` directories may contain real archived sessions. They must be inventoried read-only before any report says thread evidence is missing.
16. Approval-review/meta threads must be counted separately and must not be treated as model implementation, training, or research progress.
17. Active SQLite counts must be frozen with timestamp and read-only mode. If `PRAGMA integrity_check` fails or WAL/indexes are live, report index-assisted counts as suspect and prefer `NOT INDEXED` plus rollout parsing.
18. `goals_1.sqlite` is current goal state, not full history. Do not infer that old goals were absent merely because only one active goal remains.

## 10. Skills Or Workflow Modules That Should Be Added

1. `care-completion-auditor`

   A repo-local skill that classifies each task/result into the four completion states and rejects false completion.

2. `care-methodology-gate`

   A skill with mechanism checklists for encoder-decoder, registration, Cine temporal, SRR/retrieval/proposal, T2-edema, and submission packaging.

3. `care-evidence-inventory`

   A script/skill that indexes task/result/log/metric/job/commit evidence, flags stale or missing artifacts, and reports checkout divergence between `/users` and `/overflow`.

4. `care-slurm-evidence-check`

   A light checker that verifies job ID, log path, state, elapsed time, checkpoint, and prediction outputs before a result can claim formal evidence.

5. `care-hosted-metric-contract`

   A skill or template fragment that forces every model result to say whether it is local compact fold0, local five-fold, validation package, or hosted metric evidence.

6. `care-external-method-adapter`

   A workflow module that separates resource audit, install/import smoke, one-case adapter, fold0 metric, and rollback.

7. `care-monthly-review`

   A read-only monthly audit skill that lists tasks whose claimed status exceeds their evidence.

8. `care-codex-home-inventory`

   A read-only skill/script that records launcher path, active `CODEX_HOME`, stable home contents, legacy `.codex-homes/*CARE*`, thread counts, rollout paths, goal rows, approval/meta thread counts, and missing rollout files.

9. `care-runtime-continuity-review`

   A workflow module for Codex startup/resume/goal failures that distinguishes active UI, tmux shell continuity, SQLite state, goals DB state, rollout JSONL availability, live process locks, and approval-review status.

## 11. Definition Of Done For Future CARE Tasks

For any model-improvement task, `TRUE_DONE` requires all of the following:

- The task states its mechanism class and forbidden substitutes.
- The implemented mechanism is shown by file paths and key class/function names.
- The run has a Slurm job ID or explicit local command, exit status, elapsed time, and log path.
- The result lists checkpoint, prediction, metric, config/cache directories, and they are isolated by task/variant/fold/checkpoint.
- The evaluation uses full-volume predictions, not crop-only or proxy-only metrics.
- The result reports `myops_scar` and/or `myops_edema` for MyoPS, and `myocardium_cinemyops` or a clearly caveated local proxy for Cine.
- MyoPS reports all-cases, GT-positive/T2-present, no-T2 empty-GT stability, center B/C, HD95, component count, remote FP, and volume ratio when relevant.
- Cine reports reference frame, non-reference frame use, transform/alignment type, temporal aggregation, pathology head availability, and hosted-metric caveat.
- The result compares against the correct baseline on the same split.
- The result has a promotion decision: `GO_FOLD_EXPAND`, `GO_SUBMISSION_PACKAGE`, `REVISE`, or `STOP`.
- If evidence is missing, the result says `未找到证据` rather than inferring completion.
- If the task is an audit of Codex/GPT work, it must include external Codex-home inventory, not only repo-local `.codex` or `archive/.vibe/codex_runtime`.
- If thread evidence is used, each important claim should cite thread ID, rollout path, and whether the thread is implementation, approval/meta, watchdog, or artifact-only planning.

## 12. Escalation Rules When Simple Methods Fail

- If preflight passes but no metric exists, the next step is bounded fold0 train/eval, not another preflight.
- If fold0 gives weak Dice but bad HD95/component/remote-FP, the next step must address spatial mechanism, not fold expansion or upload.
- If SRR/proposal remains below nnU-Net after two substantive variants, stop or switch to a clearly stronger mechanism; do not continue only with temperature/gate/threshold changes.
- If registration translation gives near-zero delta, future work must try affine/deformable/TPS/feature-level alignment with warp plausibility checks, or explicitly stop Cine registration.
- If Cine reference control beats temporal variants, future Cine work must specify ED/reference motion, non-reference frame warping, and pathology aggregation before further training.
- If external repo work stops at import/shape smoke, the next authorized step must be one-case adapter plus fold0 metric, or mark `NOT_DONE`.
- If GPU queue blocks formal evidence, record pending state and queue evidence; do not substitute CPU-only crawl as formal model evidence.
- If a route has `selected_variant: none` or `STOP_*`, any upload/fold expansion proposal must be rejected unless the user explicitly overrides.

## 13. Recommended Monthly Review Prompt

```text
只读审计 CARE 最近一个月的 prompts/tasks、results、logs、jobs、git commits 和关键代码。
按 TRUE_DONE / PARTIAL_MECHANISM_INCOMPLETE / PREFLIGHT_SMOKE_ONLY / NOT_DONE 给每个 task 分类。
特别检查：
- 是否把 smoke/preflight/dryrun/readiness 当完成；
- 是否有真实 checkpoint、prediction、metric、Slurm/job log；
- 是否有 label mapping、cache isolation、hosted metric 和 one-zip submission 证据；
- 是否出现 shallow encoder-decoder、translation-only registration、frame0-only Cine、dictionary-only SRR、clone-only external method；
- 是否在 STOP/REVISE/selected_variant none 后仍计划 fold expansion、validation package 或 upload；
- 是否记录 inherited CODEX_HOME、new-launch wrapper default、旧 .codex-homes、state_5.sqlite integrity、goals_1.sqlite、rollout JSONL、session_index completeness 和 approval/meta thread；
- 是否把 approval-review/meta thread、watchdog stale artifact 或 artifact-only VibeResearch loop 当成 CARE 方法进展。
输出表格：task_key, claimed_status, audited_status, evidence_paths, thread_ids, rollout_paths, missing_evidence, blocked_promotion_reason, next_rule_update。
不得修改代码、不得提交 job、不得上传。
```

## 14. Appendices With Evidence Table

| Topic | Audited status | Evidence | Key details |
| --- | --- | --- | --- |
| Checkout divergence | Evidence gap | `/users` latest `b634a3f`; `/overflow` latest `4d76500` | `/users` has 2026-06-30 to 2026-07-02 evidence missing from `/overflow`. |
| Codex thread store inside repo | Repo-local gap only | `.codex/`, `archive/.vibe/codex_runtime/state_5.sqlite` | No complete thread DB inside either CARE checkout; only one irrelevant placeholder Vibe thread in repo-local archive. |
| T2 missingness audit | Truly useful / partial model relevance | `results/20260620_t2_edema_pilot/result.md` | Train composition `80` complete, `24` C0+LGE, `116` LGE-only; no-T2 not edema negative. |
| Submission semantics | Truly useful engineering rule | `AGENTS.md`; `scripts/submission/prepare_care_myocardium_validation.py`; `results/submissions/.../upload_ready/README.md` | One zip, three metrics; raw label remapping documented. |
| SRR spec smoke | `PREFLIGHT_SMOKE_ONLY` | `results/20260621_srr_spec/result.md`; commit `5de523e` | One-batch/unit smoke, no formal Slurm job at spec stage. |
| SRR fold0 | `PARTIAL_MECHANISM_INCOMPLETE` | `results/20260621_srr_fold0/result.md` | Jobs `55723114`, `55723115`; `REVISE_ROUTING`; scar gate concentrated expert1 mean `0.9431`. |
| Dictionary bank | `PARTIAL_MECHANISM_INCOMPLETE` | `results/20260626_dict_bank/failure_interpretation.md` | Jobs `56611484`-`56611488`; D4 selected, but HD95/component/remote-FP remained high. |
| Cine geometry | Useful preflight | `results/20260625_cine_geometry/result.md` | 59 safe cases, 5 mismatch cases; class_3 scar sanity `0.0000`. |
| Cine temporal | `PREFLIGHT_SMOKE_ONLY` / partial proxy | `results/20260626_cine_temporal/failure_interpretation.md` | Frozen CineMA anatomy prior; cannot validate scar. |
| Cine registration | `PREFLIGHT_SMOKE_ONLY` | `results/20260628_cine_register/failure_interpretation.md`; `results/20260629_cine_motion_alignment/selection.md` | SimpleITK translation delta class_1 `0.0001`, class_2 `0.0000`; `SELECT_MOTION_DESCRIPTOR_ONLY`. |
| Result5 proposal | `PARTIAL_MECHANISM_INCOMPLETE` | `results/20260628_myops_proposal/failure_interpretation.md` | Best edema GT-positive `0.2034`, scar did not improve, HD95/component burden high. |
| Hard-negative memory | `PREFLIGHT_SMOKE_ONLY` | `results/20260629_proposal_memory_hardneg/selection.md` | Mining/preflight only; no formal replay route selected. |
| Repaired proposal | `PARTIAL_MECHANISM_INCOMPLETE` | `/users/.../results/20260629_repaired_proposal_repeat/selection.md` | `ROUTE_TO_CASCADE_TEACHER`; scar `0.1038`, edema GT+ `0.1545`; no fold expansion/upload. |
| True soft-ROI refine | `PREFLIGHT_SMOKE_ONLY` | `/users/.../results/20260629_true_soft_roi_refine/selection.md` | ROI rows `88`, restoration invalid rows `0`; formal refinement not launched. |
| SRR-v2 U-Net core | `PARTIAL_MECHANISM_INCOMPLETE` | `/users/.../results/20260629_srr_v2_unet_core/selection.md`; `src/care_myocardium/models/srr_v2_unet.py` | Real multiscale route, but `STOP_NO_SRR_V2_SIGNAL`; best scar `0.2474`, edema GT+ `0.1855`. |
| Cascade teacher | `PARTIAL_MECHANISM_INCOMPLETE` | `/users/.../results/20260629_cascade_teacher_route/failure_interpretation.md` | Three formal variants completed and exported `44/44` predictions; no material improvement. |
| External method screening | `PREFLIGHT_SMOKE_ONLY` / partial | `results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration/`; Round17 MedNeXt artifacts | Mostly import/shape smoke or very-short failed runs; no hosted evidence. |
| Leaderboard evidence | Stale for current date | `results/leaderboard/*latest*` | Latest mtime from 2026-06-19; not a 2026-07-02 refresh. |
| Active external Codex home | Evidence found but DB indexes damaged | `/overflow/htzhu/mingcheng_new/.codex-home/state_5.sqlite`; wrapper files `/overflow/htzhu/mingcheng_new/bin/codex` and `conda/bin/codex` | New wrapper launches force stable home, but current process inherited `.codex-homes/CARE`; `PRAGMA integrity_check` failed, so counts require `NOT INDEXED` plus rollout parse. |
| Main thread-count discrepancy | Evidence found | `PRAGMA integrity_check`; `threads NOT INDEXED`; direct `sessions/**/*.jsonl` parse; `session_index.jsonl` | `session_index.jsonl` had 503 lines, direct rollout scan had 562 files, exact CARE cwd was 265 by table scan and 261 by rollout parse; index-assisted counts were inconsistent. |
| Legacy CARE homes | Evidence found | `/overflow/htzhu/mingcheng_new/.codex-homes/overflow_htzhu_CARE`; `.codex-homes/CARE` symlink duplicate; `.codex-homes/overflow_htzhu_CARE_vibe_research`; `.codex-homes/CARE__tmux_codex-care`; `.codex-homes/CARE__tmux_care-vibe-watchdog` | 116, 97, 29, and 16 indexed thread/session pools; `CARE` duplicates `overflow_htzhu_CARE`; `session_index.jsonl` is incomplete in several homes. |
| Daemon rollout pool | Partial evidence / not exhaustively parsed | `.codex-homes/CARE__tmux_vibe-CARE-8da3ac9f-daemon/sessions/**/*.jsonl` | SQLite thread count was 0 but rollout files were 4,029; future audit must parse JSONL directly. |
| Active goal state | Current-state only | `/overflow/htzhu/mingcheng_new/.codex-home/goals_1.sqlite`; thread `019efa60-c382-7a33-b889-b8d60a8ae476` | One active Result5 continuation sprint goal; goals DB is not a full historical ledger. |
| U-MyoPS thread evidence | Thread evidence found | `019debd7-ae46-7a60-81ea-4e165105d70f`; rollout under `.codex-home/sessions/2026/05/02/` | Confirms external thread history includes early U-MyoPS dataflow/dimension audit. |
| MyoPS-Net thread evidence | Thread evidence found | `019debf6-cc3f-7e53-a157-cc5a79b5f30e`; rollout under `.codex-home/sessions/2026/05/02/` | Confirms external thread history includes low-performance model audit. |
| CineMyoPS thread evidence | Thread evidence found | `019decaa-2810-73e3-8b15-2907310b37e6`; `019ee0d0-846c-7532-94f8-1aeea2ba20f8` | Covers CineMyoPS scar/class audit and CineMA adapter pilot. |
| VibeResearch artifact-only loop | `PARTIAL_MECHANISM_INCOMPLETE` / workflow failure | thread `019eb5e1-7c12-7582-b101-2a6ad57d3a11`; `archive/.vibe/results/c037/*.json` | Structured artifacts reached `completed_evidence`/`validator_pass`, but decisions were `REPAIR`/`STOP` and `safe_to_promote_runtime_experiment=false`. |
| Approval-review noise | Not task completion | thread `019edf2e-7866-7f20-b1bb-fb7f0b377421`; approval-review title prefix | Approval/self-review transcripts should be classified separately from CARE model work. |
| Watchdog/live-state drift | Partial/uncertain | thread `019e9c5a-b477-7f53-b31c-26330c811880`; archived `code/archive/Inspect/watchdog_state/*` | Stale watchdog artifacts existed; live daemon truth diverged and MedNeXt route selection remained a workflow enforcement problem. |

## Final Audit Judgment

Codex/GPT did useful engineering and produced several honest negative results, but the CARE research plan was repeatedly narrowed into easier proxies. The new external-home evidence strengthens, rather than weakens, that conclusion: the missing threads show repeated attempts, meta-reviews, approvals, watchdog cycles, and artifact-only planning, not hidden completed mechanisms. The next workflow should not ask agents to “continue improving” without a hard completion schema. It should force every task to declare its mechanism, forbidden shallow substitutes, required evidence, promotion gate, thread/runtime provenance, and four-way completion status before any result can be called done.
