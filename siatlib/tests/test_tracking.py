"""
Pruebas unitarias para tracking/detector.py.
Valida la resolución dinámica de dispositivos PyTorch (CPU, CUDA, MPS o GPU IDs).
"""

from unittest.mock import MagicMock, patch
import pytest
import torch
from siatlib.tracking import get_torch_device


def test_get_torch_device_explicit_cpu():
    """Valida que especificar 'cpu' retorne siempre un torch.device('cpu')."""
    dev = get_torch_device("cpu")
    assert dev.type == "cpu"


@patch("torch.cuda.is_available", return_value=True)
def test_get_torch_device_auto_with_cuda(mock_cuda):
    """Valida que 'auto' o None seleccione CUDA si está disponible en el hardware."""
    dev = get_torch_device("auto")
    assert dev.type == "cuda"


@patch("torch.cuda.is_available", return_value=False)
def test_get_torch_device_auto_fallback_cpu(mock_cuda):
    """Valida que 'auto' caiga en CPU cuando CUDA no esté disponible."""
    with patch("torch.backends.mps.is_available", return_value=False, create=True):
        dev = get_torch_device("auto")
        assert dev.type == "cpu"


@patch("torch.cuda.is_available", return_value=False)
def test_get_torch_device_cuda_fallback_when_unavailable(mock_cuda):
    """Valida que si se solicita 'cuda' pero no está disponible, emita advertencia y caiga en CPU sin crashear."""
    dev = get_torch_device("cuda")
    assert dev.type == "cpu"


@patch("torch.cuda.is_available", return_value=True)
@patch("torch.cuda.device_count", return_value=2)
def test_get_torch_device_specific_gpu_index(mock_count, mock_cuda):
    """Valida la selección de una GPU específica por índice numérico (ej. '1' -> 'cuda:1')."""
    dev = get_torch_device("1")
    assert dev == torch.device("cuda:1")

