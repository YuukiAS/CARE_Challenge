# Model Selection Rationale

Scar: CARE-DG A3 step5000; complete16 Dice 0.695876; nnU-Net 0.693335. It is used because it is the frozen self-owned scar model that slightly beats the nnU-Net anchor on the complete-trimodal fold0 reproduction evidence.

Edema: SCR control_seed20260724; complete16 class-4 Dice 0.401277; nnU-Net 0.394436. It is used because this task is an exploratory hosted-format probe of the candidate pure-edema output, not the previous conservative FALLBACK_TO_NNUNET safety decision.

Anatomy: Dataset501 nnU-Net five-fold anchor; raw labels 200/500/600 are restored to match the historical nnU-Net validation ZIP output class contract. Anatomy is not a primary leaderboard objective here.

Cine: frozen historical implementation from the 20260520 recommended tree; it is reused unchanged to keep the Cine branch stable while probing MyoPS pathology.
