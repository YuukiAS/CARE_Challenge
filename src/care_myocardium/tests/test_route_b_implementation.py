import torch

from src.care_myocardium.route_B import RouteBCineModel, RouteBMyoPSModel, route_b_cine_loss, route_b_myops_loss


def test_route_b_myops_forward_loss_backward() -> None:
    model = RouteBMyoPSModel()
    x = torch.randn(2, 3, 8, 12, 12)
    availability = torch.tensor([[1, 1, 1], [1, 1, 0]], dtype=torch.float32)
    anchor = torch.randn(2, 6, 8, 12, 12)
    labels = torch.zeros(2, 8, 12, 12, dtype=torch.long)
    labels[0, 2:5, 3:8, 3:8] = 4
    labels[1, 3:6, 4:9, 4:9] = 5
    out = model(x, availability, anchor)
    loss, parts = route_b_myops_loss(out, labels, availability)
    assert torch.isfinite(loss)
    assert parts["total"] > 0
    loss.backward()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.parameters())


def test_route_b_cine_forward_loss_backward() -> None:
    model = RouteBCineModel()
    frames = torch.randn(2, 4, 1, 8, 12, 12)
    target = torch.zeros(2, 8, 12, 12, dtype=torch.long)
    target[:, 2:6, 3:8, 3:8] = 1
    out = model(frames)
    loss, parts = route_b_cine_loss(out, target)
    assert torch.isfinite(loss)
    assert parts["total"] > 0
    loss.backward()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in model.parameters())
