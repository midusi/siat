import os
#import wandb
from ultralytics import YOLO
from pathlib import Path

FROM_SCRATCH = False

# Directorio raíz de experiments (siatlib/src/experiments)
EXPERIMENTS_DIR = Path(__file__).resolve().parents[2]

FROM_SCRATCH_MODEL_BASE = "yolo11s.pt"
FINETUNING_MODEL_BASE = str(EXPERIMENTS_DIR / "scripts/models/siatv1-v5/y11m-lh-sinvan.pt")

config = {
    # Trazabilidad
    "experiment_id": "SIATLIB-V1",
    "run_id": "traffic-finetuning-y11s-lr001-1280px-aug",
    "seed": 42,

    # Modelo y Dataset
    "from_scratch": FROM_SCRATCH,
    "model_base": FROM_SCRATCH_MODEL_BASE if FROM_SCRATCH else FINETUNING_MODEL_BASE, 

    "data": str(EXPERIMENTS_DIR / "dataset/process/test1/data.yaml"),
    "epochs": 300 if FROM_SCRATCH else 100,
    "imgsz": 1280,
    "batch": 4, # 2 o 4 para GPU con poca VRAM; 8 si mas; -1 auto
    "device": 0, # 0 GPU, "cpu" CPU

    "patience": 15,

    "optimizer": "SGD" if FROM_SCRATCH else "AdamW",
    "lr0": 0.01,

    "mosaic": True,
    "mixup": 0.5,

    "freeze": 0 if FROM_SCRATCH else 10,
    "project": str(EXPERIMENTS_DIR / "runs"),
    # "output_figures_dir": str(EXPERIMENTS_DIR / "reports/figures"),
    # "output_result_dir": str(EXPERIMENTS_DIR / "reports/models")
}