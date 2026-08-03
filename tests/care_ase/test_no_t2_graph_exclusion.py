import torch

from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.models.care_ase import build_care_ase_for_fold


def test_no_t2_all_batch_does_not_call_edema_owned_modules():
    model = build_care_ase_for_fold(2)
    calls = {"edema_branch": 0, "edema_dilation": 0, "edema_adapter": 0}

    handles = [
        model.edema_branch.register_forward_hook(lambda *_args: calls.__setitem__("edema_branch", calls["edema_branch"] + 1)),
        model.edema_dilation_context.register_forward_hook(lambda *_args: calls.__setitem__("edema_dilation", calls["edema_dilation"] + 1)),
        model.edema_t2_half_adapter.register_forward_hook(lambda *_args: calls.__setitem__("edema_adapter", calls["edema_adapter"] + 1)),
        model.edema_c0_half_adapter.register_forward_hook(lambda *_args: calls.__setitem__("edema_adapter", calls["edema_adapter"] + 1)),
        model.edema_lge_half_adapter.register_forward_hook(lambda *_args: calls.__setitem__("edema_adapter", calls["edema_adapter"] + 1)),
    ]
    try:
        sample = torch.randn(1, 3, 8, 64, 64)
        availability = torch.tensor([[1.0, 0.0, 1.0]])
        outputs = model(sample, availability, global_step=6000)
    finally:
        for handle in handles:
            handle.remove()

    decoded = decode_care_ase_r2_logits(outputs["final_logits"], availability)
    assert calls == {"edema_branch": 0, "edema_dilation": 0, "edema_adapter": 0}
    assert outputs["no_t2_edema_graph_excluded"] is True
    assert int((decoded == 4).sum()) == 0
