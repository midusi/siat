import os
#import wandb
from ultralytics import YOLO
from pathlib import Path

FROM_SCRATCH = True

BASE_DIR = Path(__file__).resolve().parent

config = {
    # Trazabilidad
    "experiment_id": "SIATLIB-V1",
    "run_id": "traffic-scratch-y11m" "traffic-v1a-y11m-lr001-1280px-aug",
    "seed": 42,

    # Modelo y Dataset
    "from_scratch": FROM_SCRATCH,
    "model_base": "yolo11s.pt" if FROM_SCRATCH else "yolo11m.yaml", 


    "data": "../../dataset/process/test1/data.yaml",
    "epochs": 300 if FROM_SCRATCH else 100,
    "imgsz": 1280,
    "batch": 4, # 2 o 4 para GPU con poca VRAM; 8 si mas; -1 auto
    "device": 0, # 0 GPU, "cpu" CPU

    "patience": 15,
    

    "optimizer": "SGD" if FROM_SCRATCH else "AdamW",
    "lr0": 0.01,

    "mosaic":True,
    "mixup":0.5,

    #"freeze": 0 if FROM_SCRATCH else 10
    "project": str(BASE_DIR / "runs"),
    "output_figures_dir": str(BASE_DIR / "reports/figures"),
    "output_result_dir": str(BASE_DIR / "reports/models")

}