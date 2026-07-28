import numpy as np

from src.care_myocardium.inference.care_dg_full_volume import compose_scar_priority_numpy


def test_scar_priority_composition_keeps_class5_over_edema_zone():
    anchor_logits = np.zeros((6, 1, 1, 3), dtype=np.float32)
    edema_delta = np.zeros((1, 1, 1, 3), dtype=np.float32)
    scar_delta = np.zeros((1, 1, 1, 3), dtype=np.float32)
    scar_delta[0, 0, 0, 1] = 10.0
    edema_delta[0, 0, 0, 1] = 10.0
    edema_delta[0, 0, 0, 2] = 10.0

    _, final_logits = compose_scar_priority_numpy(
        anchor_logits,
        scar_delta,
        edema_delta,
        scar_margin_cap=5.0,
        edema_margin_cap=5.0,
        direct_residual=False,
    )
    final_mask = final_logits.argmax(axis=0)

    assert final_mask[0, 0, 1] == 5
    assert final_mask[0, 0, 2] == 4
