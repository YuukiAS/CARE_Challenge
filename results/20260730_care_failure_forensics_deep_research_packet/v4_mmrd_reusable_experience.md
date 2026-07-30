# MMRD reusable experience

MMRD V4 binds 8 checkpoints and 704 casewise rows from matched seeds.

- Reliable-label and no-T2 hygiene: retain as data rules.
- Modality dropout: retain as a training strategy to test, not as proof of model gain.
- Distillation: mean distill-minus-direct Dice across comparable rows is -0.175652; mean distill-minus-moddrop Dice is 0.024861. This is mechanism evidence, not a successful candidate.
- Simple residual head: do not reuse as implemented unless future evidence restores decoder capability and beats the same-split nnU-Net baseline.
- Component-effect source rows: 176.
