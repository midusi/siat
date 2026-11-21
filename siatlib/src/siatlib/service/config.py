"""Configuración del servicio a partir de variables de entorno (sección 7 del contrato)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ServiceSettings:
    data_dir: Path = Path("/data")
    models_dir: Path = Path("/models")
    default_model: str = "model.pt"
    device: str = "auto"
    tracker_config: Optional[str] = None
    host: str = "0.0.0.0"
    port: int = 8000
    poll_interval: float = 1.0

    @property
    def input_dir(self) -> Path:
        return self.data_dir / "input"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "siat-service.db"

    @classmethod
    def from_env(cls) -> "ServiceSettings":
        env = os.environ
        return cls(
            data_dir=Path(env.get("SIAT_DATA_DIR", "/data")),
            models_dir=Path(env.get("SIAT_MODELS_DIR", "/models")),
            default_model=env.get("SIAT_DEFAULT_MODEL", "model.pt"),
            device=env.get("SIAT_DEVICE", "auto"),
            tracker_config=env.get("SIAT_TRACKER_CONFIG") or None,
            host=env.get("SIAT_HOST", "0.0.0.0"),
            port=int(env.get("SIAT_PORT", "8000")),
            poll_interval=float(env.get("SIAT_POLL_INTERVAL", "1.0")),
        )

    def ensure_dirs(self) -> None:
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
