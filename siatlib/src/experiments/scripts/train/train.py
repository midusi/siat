from ultralytics import YOLO
from config import config
from dotenv import load_dotenv
import wandb
import os

load_dotenv()  # Busca .env en el directorio actual


def main():
    """
    Función principal para configurar y ejecutar el entrenamiento de un modelo YOLO
    para el análisis de tráfico desde drones.
    """

    #wandb.login()
    wandb.login(key=os.getenv("WANDB_API_KEY"))   

    run = wandb.init(
      entity=config["entity_id"],
      project = config["experiment_id"],
      name = f"{config["experiment_id"]}_{config["run_id"]}",
      config = config,
      reinit=True
    )
 

  
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
        project=config["project"],
        name=config["run_id"],
        exist_ok=True,
      )
    # FINE-TUNING
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
            name=config["run_id"],
            exist_ok=True,
            #output_dir=config["output_result_dir"],
        )

    print("Entrenamiento finalizado.")
    print(f"Los mejores pesos (best.pt) se han guardado en la carpeta: {results.save_dir}")

    artifact = wandb.Artifact(
      name=f"model-{config["run_id"]}",
      type="model",
      description=f"Pesos de {config["run_id"]} entrenados sobre {config["data"]}"

    )
    artifact.add_file(f"{results.save_dir}/args.yaml")
    artifact.add_file(f"{results.save_dir}/weights/best.pt")
    artifact.add_file(f"{results.save_dir}/results.csv")
    run.log_artifact(artifact)

    wandb.finish()

if __name__ == '__main__':
    main()
