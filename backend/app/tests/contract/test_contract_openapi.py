"""Congela el esquema OpenAPI: rutas, métodos, parámetros y forma de las respuestas.

Si un cambio es intencional, regenerar con:
    UPDATE_OPENAPI_SNAPSHOT=1 python -m pytest app/tests/contract/test_contract_openapi.py
"""
import json
import os
from pathlib import Path

from app.main import app

SNAPSHOT = Path(__file__).parent / "snapshots" / "openapi.json"


def _render(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_openapi_schema_matches_snapshot():
    current = _render(app.openapi())

    if os.getenv("UPDATE_OPENAPI_SNAPSHOT") == "1":
        SNAPSHOT.write_text(current, encoding="utf-8")

    assert SNAPSHOT.exists(), "Falta el snapshot; generarlo con UPDATE_OPENAPI_SNAPSHOT=1"
    assert current == SNAPSHOT.read_text(encoding="utf-8")
