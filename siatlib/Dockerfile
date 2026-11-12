# siatlib — servicio de inferencia (API HTTP + cola).
# Contrato: docs/SIATLIB_SERVICE_API.md
#
# GPU (por defecto):
#   docker build -t siatlib/inference siatlib/
#
# Solo CPU (imagen más liviana, útil para probar sin GPU):
#   docker build -t siatlib/inference:cpu \
#     --build-arg BASE_IMAGE=python:3.12-slim \
#     --build-arg TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu \
#     siatlib/

ARG BASE_IMAGE=pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
FROM ${BASE_IMAGE}

# Si se indica, instala torch desde ese índice antes que el resto (p. ej. CPU-only).
ARG TORCH_INDEX_URL=""

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    SIAT_DATA_DIR=/data \
    SIAT_MODELS_DIR=/models \
    SIAT_DEFAULT_MODEL=model.pt \
    SIAT_DEVICE=auto \
    SIAT_HOST=0.0.0.0 \
    SIAT_PORT=8000

# Librerías de sistema que necesita OpenCV (ultralytics trae opencv-python) y curl para el healthcheck.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 curl \
 && rm -rf /var/lib/apt/lists/*

RUN if [ -n "$TORCH_INDEX_URL" ]; then \
        pip install torch torchvision --index-url "$TORCH_INDEX_URL"; \
    fi

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[service]"

VOLUME ["/data", "/models"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://localhost:${SIAT_PORT}/health" || exit 1

CMD ["siat-service"]
