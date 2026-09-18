"""Tests for depth estimation helpers — no model needed."""

import pytest

from app.infrastructure.vision.depth import resolve_device


def _torch_with_cuda():
    """Import torch, skipping when absent or without a cuda subpackage."""
    torch = pytest.importorskip("torch")
    if not hasattr(torch, "cuda"):
        pytest.skip("torch installed without cuda support")
    return torch


class TestResolveDevice:
    def test_explicit_devices_pass_through(self) -> None:
        assert resolve_device("cpu") == "cpu"
        assert resolve_device("0") == "0"

    def test_auto_resolves_to_cpu_without_cuda(self, monkeypatch) -> None:
        torch = _torch_with_cuda()
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

        assert resolve_device("auto") == "cpu"

    def test_auto_resolves_to_cuda_when_available(self, monkeypatch) -> None:
        torch = _torch_with_cuda()
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)

        assert resolve_device("auto") == "cuda"
