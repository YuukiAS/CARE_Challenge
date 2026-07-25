#!/bin/bash
# Poll SLURM and advance the MoSAIC paper pipeline automatically:
#   training finishes -> submit full-pipeline evals -> regenerate tables -> recompile.
# Safe to run repeatedly; every step it calls is idempotent.
#
# Usage: nohup bash scripts/watch_and_advance.sh > logs/watch.log 2>&1 &

# Deliberately no `set -e`/`pipefail`: this is a long-lived monitor, and a
# transient failure (empty glob, a job that has not written output yet) must not
# kill the loop.
cd "$(dirname "$0")/.." || exit 1
ROOT=$(pwd)
source ~/.bashrc
conda activate stai_tune

INTERVAL=600          # 10 min between checks
MAX_HOURS=48
deadline=$(( $(date +%s) + MAX_HOURS * 3600 ))

log () { echo "[$(date '+%F %T')] $*"; }

log "watcher started (interval ${INTERVAL}s, max ${MAX_HOURS}h)"

while [ "$(date +%s)" -lt "$deadline" ]; do
    running=$(squeue -u "$USER" -h -o "%j" 2>/dev/null | grep -c '^mos_')
    trained=$(find ablations -name experiment_result.json 2>/dev/null | wc -l)
    evaled=$(find paper/results -name '*.json' 2>/dev/null | wc -l)
    log "queue=${running}  trained_runs=${trained}  eval_results=${evaled}"

    # Submit evaluation for any variant whose 5 folds have all landed.
    python scripts/submit_ablation_evals.py 2>&1 | sed 's/^/    /' || log "submit_ablation_evals failed (continuing)"

    # Refresh tables and recompile with whatever is available so far.
    python scripts/make_paper_tables.py > /dev/null 2>&1 || log "make_paper_tables failed"
    ( cd paper \
      && pdflatex -interaction=nonstopmode mosaic.tex > /dev/null 2>&1 \
      && bibtex mosaic > /dev/null 2>&1 \
      && pdflatex -interaction=nonstopmode mosaic.tex > /dev/null 2>&1 \
      && pdflatex -interaction=nonstopmode mosaic.tex > /tmp/mosaic_pass.log 2>&1 ) || log "pdflatex failed"
    pages=$(grep -o "mosaic.pdf ([0-9]* pages" /tmp/mosaic_pass.log 2>/dev/null | grep -o '[0-9]*')
    [ -z "$pages" ] && pages="?"
    placeholders=$(grep -l -- "--" paper/tables/*.tex 2>/dev/null | wc -l)
    log "    paper: ${pages} pages, ${placeholders} tables still with placeholders"

    if [ "$running" -eq 0 ]; then
        # Nothing queued. If every expected eval has landed we are done.
        if [ "$evaled" -ge 15 ]; then
            log "ALL DONE: no jobs queued and ${evaled} eval results present"
            exit 0
        fi
        # Give submit_ablation_evals one cycle to queue new work before giving up.
        sleep "$INTERVAL"
        if [ "$(squeue -u "$USER" -h -o '%j' 2>/dev/null | grep -c '^mos_')" -eq 0 ]; then
            log "STALLED: queue empty but only ${evaled} eval results. Check ablations/*/_logs/*.err"
            exit 1
        fi
        continue
    fi
    sleep "$INTERVAL"
done

log "watcher hit ${MAX_HOURS}h limit"
exit 2
