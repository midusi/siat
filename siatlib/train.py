from ultralytics import YOLO

def main():
    """
    Función principal para configurar y ejecutar el entrenamiento de un modelo YOLO
    para el análisis de tráfico desde drones.
    """
    # --- 1. Cargar el modelo base ---
    model = YOLO('yolo11m.pt')

    # --- 2. Iniciar el entrenamiento ---
    results = model.train(
      # --- Datos ---
      data='datasets/dataset-v5/data.yaml',
      epochs=100,                 # suficiente para dataset pequeño
      imgsz=1280,                 # buena resolución para objetos pequeños
      batch=2,                    # estable para GPU promedio
      nbs=4,
      device=0,                   # GPU

      # --- Regularización y early stopping ---
      patience=15,                # detiene si no hay mejora en val loss
      seed=42,                    # reproducibilidad

      # --- Optimización ---
      optimizer='AdamW',          # recomendado para dataset pequeño
      lr0=0.01,                   # learning rate inicial
      weight_decay=0.0005,        # regularización

      # --- Augmentation ---
      mosaic=True,                # combina 4 imágenes en 1
      mixup=0.5,                  # mezcla 2 imágenes con etiquetas
      auto_augment='randaugment', # política de auto-augmentation

      # --- Organización ---
      project='runs',
      name='traffic-v5b-y11m-1280px-100e-aug',
      exist_ok=True,
    )

    print("Entrenamiento finalizado.")
    print(f"Los mejores pesos (best.pt) se han guardado en la carpeta: {results.save_dir}")

if __name__ == '__main__':
    main()
