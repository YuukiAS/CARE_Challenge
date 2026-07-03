# Failure Interpretation

decision: NEEDS_EVIDENCE
scientific_resolution_status: SCIENTIFIC_NEEDS_EVIDENCE

## Interpretation

This is not a learned route failure and not a scientific stop. The learned anchor-refine task could not proceed because prerequisite evidence was insufficient:

- The SRR PropRef repair review found undertrained evidence and no route promotion.
- The nnU-Net OOF component review found useful diagnostic postprocess evidence, but explicitly blocked learned anchor-refine execution from that audit alone.

The correct executor outcome is therefore `NEEDS_EVIDENCE`, not `STOP_NO_LEARNED_ANCHOR_SIGNAL`.

## Why Training Was Not Run

The task says to use learned anchor refine only after reviewed prerequisite evidence exists from the SRR repair and component scorer tasks. Current reviewed evidence is diagnostic-only. Running training anyway would convert diagnostic publication into unauthorized next-stage training.

## Blocked Actions

- learned training
- fold expansion
- validation packaging
- validation upload
- hosted metric claims
- label/evaluator/fold split changes
- route promotion
- route-negative scientific stop

## Required Evidence For A Future Learned Run

- usable reviewed input definition for the learned refiner
- one-batch overfit sanity
- minimum effective optimizer steps and train-loop seconds
- validation events and loss decrease
- checkpoint path
- prediction path
- metric CSV
- same-split nnU-Net baseline comparison
- prediction sanity and label/export QC
- independent audit
