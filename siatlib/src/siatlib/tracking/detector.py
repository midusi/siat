import torch
from typing import Optional

def get_torch_device(preferred_device: Optional[str]) -> torch.device:
    """
    Determina el dispositivo PyTorch a usar (CPU o GPU) basado en la preferencia
    y la disponibilidad del hardware.
    """
    if not torch.cuda.is_available():
        print("Usando CPU (CUDA no disponible)")
        return torch.device("cpu")
        
    if preferred_device == "cpu":
        return torch.device("cpu")
    elif preferred_device == "auto":
        return torch.device("cuda")
    elif preferred_device and preferred_device.isdigit():
        if int(preferred_device) < torch.cuda.device_count():
            return torch.device(f"cuda:{preferred_device}")
        else:
            print(f"Advertencia: GPU '{preferred_device}' no disponible o no válida. Usando CPU.")
            return torch.device("cpu")
    elif preferred_device and "cuda" in preferred_device:
         return torch.device(preferred_device)
    else:
        return torch.device("cuda")
