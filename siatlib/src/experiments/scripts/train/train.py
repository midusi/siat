from ultralytics import YOLO
from config import config



def main():
    """
    Función principal para configurar y ejecutar el entrenamiento de un modelo YOLO
    para el análisis de tráfico desde drones.
    """

    
    model = YOLO(config["model_base"])  # O yolo11m.yaml, yolo11l.yaml, etc. según la variante

    # ENTRENAMIENTO DE MODELO 
    if(config["from_scratch"]):
      results = model.train(
        # --- Datos ---
        data=config["data"],
        epochs=config["epochs"],                 # suficiente para dataset pequeño
        imgsz=config["imgsz"],                 # buena resolución para objetos pequeños
        batch=config["batch"],                    # estable para GPU promedio
        #nbs=4,
        device=config["device"],                   # GPU
        optimizer=config["optimizer"],
        lr0=config["lr0"],

        # --- Regularización y early stopping ---
        patience=config["patience"],                # detiene si no hay mejora en val loss
        seed=config["seed"],                    # reproducibilidad

        # --- Augmentation ---
        mosaic=config["mosaic"],                # combina 4 imágenes en 1
        mixup=config["mixup"],                  # mezcla 2 imágenes con etiquetas
        auto_augment='randaugment', # política de auto-augmentation

        # --- Organización ---
        project='runs',
        name='traffic-v5b-y11m-1280px-100e-aug',
        exist_ok=True,
      )
    else:
      results = model.train(
            data=config["data"],
            epochs=config["epochs"],
            imgsz=config["imgsz"],
            batch=config["batch"],
            nbs=4,
            freeze=10,
            device=config["device"],
            patience=config["patience"],
            seed=config["seed"],
            optimizer=config["optimizer"],
            lr0=config["lr0"],
            weight_decay=0.0005,
            mosaic=config["mosaic"],
            mixup=config["mixup"],
            auto_augment='randaugment',
            project=config["project"],
            name=config["run_name"],
            exist_ok=True,
            output_dir=config["output_result_dir"],
        )

    print("Entrenamiento finalizado.")
    print(f"Los mejores pesos (best.pt) se han guardado en la carpeta: {results.save_dir}")

if __name__ == '__main__':
    main()
