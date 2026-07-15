# CARE Route Portfolio: 2026-07-15 to 2026-07-27

## Common Rules

Route A, B, C all start from the same setup commit.
Each route has an independent branch, worktree, controller, result namespace,
runtime namespace, logs, locks, finalizer, and reviewer.
No route may write another route's worktree or runtime.
No formal training may start before that route's implementation validator passes.
Root wiki/current_state is updated only during final reconciliation.

The main worktree at `/users/a/e/aereinh/CARE` is reserved for `main`,
portfolio setup, final reconciliation, and shared infrastructure. Do not develop
Route A, B, or C model code in the main worktree.

## Route Roles

Route A:
smallest workload and fastest path to a new submission candidate.

Route B:
medium workload and complete architecture implementation path.

Route C:
largest workload and continuation of the full M10 evidence/Cine fidelity path.

## Branches And Worktrees

| Route | Branch | Worktree | Controller tmux | Reviewer tmux |
| --- | --- | --- | --- | --- |
| Portfolio | `main` | `/users/a/e/aereinh/CARE` | `care_portfolio` | final reviewer only |
| Route A | `route_A` | `/users/a/e/aereinh/CARE_worktrees/route_A` | `care_route_A_controller` | `care_route_A_reviewer` |
| Route B | `route_B` | `/users/a/e/aereinh/CARE_worktrees/route_B` | `care_route_B_controller` | `care_route_B_reviewer` |
| Route C | `route_C` | `/users/a/e/aereinh/CARE_worktrees/route_C` | `care_route_C_controller` | `care_route_C_reviewer` |

Reviewer worktrees must be created only after the corresponding controller
packet commit exists. They must be fixed to the reviewed commit and must not
follow a mutable controller branch.

## Compute Routing

The shared route routing policy is in
[`configs/routes/partition_routing.yaml`](../configs/routes/partition_routing.yaml).

If there are three independent ready jobs, assign distinct work to `htzhulab`,
`a100-gpu`, and `volta-gpu` before creating duplicate mirror races.
If a single critical-path job is pending and all three partitions are eligible,
submit a three-partition race with isolated attempt directories and one shared
atomic winner lock. The first job that obtains the lock is the official attempt;
other started mirrors must write a `RACE_LOST` receipt and exit, while pending
losers are cancelled by the watcher.

V100 compatibility must be explicitly declared. Do not change model shape,
batch semantics, losses, labels, split, or scientific budget only to fit 16 GB
memory. If V100 is incompatible, use it for independent inference, checkpoint
replay shards, validators, or other light jobs.

## Daily Plan

| Date | Route A | Route B | Route C | Portfolio / shared |
|---|---|---|---|---|
| 7月15日 Day 0 | Create branch, worktree, controller environment | Create branch, worktree, controller environment | Create branch, worktree, controller environment | Clean branches, create tmux, routing, and README |
| 7月16日 Day 1 | Complete route contract and code gap list | Complete full architecture code gap list | Complete M10 inherited-state and reusable-asset inventory | Three Critics may review in parallel and do not block each other |
| 7月17日 Day 2 | Fill code gaps; no formal training | Fill all core code gaps; no formal training | Fill evidence/Cine fidelity implementation; no formal training | Check all three partitions and route isolation |
| 7月18日 Day 3 | Real-case smoke, gradient, and checkpoint validation | Full architecture forward, loss, intervention, and reload validation | Replay/Cine implementation gate | Implementation freeze per route |
| 7月19日 Day 4 | First budgeted training or evaluation | First training stage | Evidence replay and Cine first-stage runtime | Full three-partition scheduling |
| 7月20日 Day 5 | First candidate continue/stop decision | Proposal/intermediate mechanism continue/stop decision | First complete evidence/Cine decision | Summarize without merging scientific conclusions |
| 7月21日 Day 6 | Expand folds/cases after gate | Refinement or next training stage | Later runtime stages | Start Docker and package dry-run |
| 7月22日 Day 7 | Produce first candidate package | Produce full architecture single-fold candidate | Produce auditable M10/Cine candidate | Route-local reviewer starts |
| 7月23日 Day 8 | Last targeted change based on evidence | Last targeted change based on mechanism evidence | Fill remaining evidence/runtime | Compare reviewed packets |
| 7月24日 Day 9 | Freeze candidate | Freeze candidate | Freeze usable result | Docker, paper tables, figures, and submission QA |
| 7月25日 Day 10 | Final route packet | Final route packet | Final route packet | Final reconciliation and final reviewer |
| 7月26日 Buffer | Only fix runtime or packaging defects | Only fix runtime or packaging defects | Only fix runtime or packaging defects | Upload and Docker buffer |
| 7月27日 Deadline | No new scientific experiments | No new scientific experiments | No new scientific experiments | Final submission |

Day 2 and earlier must not use long training to hide missing implementation.
Routes that fail the Day 3 implementation gate may not enter formal training.
One route failing does not block the others.
A route that has not completed review must not be written into root current
state.
No new architecture or new loss may be introduced on 7月26日.

## Validation

Run the setup validator from the main worktree:

```bash
python scripts/ops/validate_route_setup.py
```

Status should be checked with:

```bash
bash scripts/ops/route_status.sh
```
