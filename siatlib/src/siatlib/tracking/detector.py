import torch
from typing import Optional

def get_torch_device(preferred_device: Optional[str] = None) -> torch.device:
    """
    Determina el dispositivo PyTorch a usar (CPU, CUDA o MPS) basado en la preferencia
    y la disponibilidad del hardware.
    """
    if torch is None:
        raise RuntimeError("PyTorch no está instalado.")

    if not preferred_device or preferred_device == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    if preferred_device == "cpu":
        return torch.device("cpu")

    if preferred_device.isdigit():
        if torch.cuda.is_available() and int(preferred_device) < torch.cuda.device_count():
            return torch.device(f"cuda:{preferred_device}")
        print(f"Advertencia: GPU '{preferred_device}' no disponible o no válida. Usando CPU.")
        return torch.device("cpu")

    if "cuda" in preferred_device:
        if torch.cuda.is_available():
            return torch.device(preferred_device)
        print("Advertencia: CUDA no disponible. Usando CPU.")
        return torch.device("cpu")

    try:
        return torch.device(preferred_device)
    except Exception:
        print(f"Advertencia: Dispositivo '{preferred_device}' desconocido. Usando CPU.")
        return torch.device("cpu")
