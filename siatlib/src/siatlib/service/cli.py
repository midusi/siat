"""Comando `siat-service`: levanta la API HTTP y el worker de inferencia."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import ServiceSettings


def main() -> None:
    env = ServiceSettings.from_env()
    parser = argparse.ArgumentParser(
        description="Servicio de inferencia de siatlib (API HTTP + cola). "
        "Los valores por defecto salen de las variables SIAT_*."
    )
    parser.add_argument("--host", default=env.host)
    parser.add_argument("--port", type=int, default=env.port)
    parser.add_argument("--data-dir", type=Path, default=env.data_dir, help="Raíz de input/, output/ y la base SQLite")
    parser.add_argument("--models-dir", type=Path, default=env.models_dir)
    parser.add_argument("--default-model", default=env.default_model)
    parser.add_argument("--device", default=env.device)
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    try:
        import uvicorn
    except ImportError:
        raise SystemExit("Falta el extra del servicio: pip install 'siatlib[service]'")

    from .api import create_app

    settings = ServiceSettings(
        data_dir=args.data_dir,
        models_dir=args.models_dir,
        default_model=args.default_model,
        device=args.device,
        tracker_config=env.tracker_config,
        host=args.host,
        port=args.port,
        poll_interval=env.poll_interval,
    )
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level=args.log_level)


if __name__ == "__main__":
    main()
