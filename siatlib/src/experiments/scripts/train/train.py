from ultralytics import YOLO

FROM_SCRATCH = True

def main():
    """
    Función principal para configurar y ejecutar el entrenamiento de un modelo YOLO
    para el análisis de tráfico desde drones.
    """

    if(FROM_SCRATCH):
      # ENTRENAMIENTO DE MODELO DESDE CERO
      model = YOLO('yolo11n.yaml')  # O yolo11m.yaml, yolo11l.yaml, etc. según la variante
      
      # Iniciar el entrenamiento desde cero
      results = model.train(
          data='datasets/dataset-v5/data.yaml',
          epochs=100,                 # Recomendado: más épocas para entrenar desde cero
          imgsz=1280,
          batch=8,
          device=0,

          patience = 15,
          seed = 42,
          
          # Optimización ajustada para entrenamiento desde cero
          optimizer='SGD',            # SGD suele funcionar mejor que AdamW al entrenar sin pesos previos
          lr0=0.01,
          
          # Augmentation (muy importante cuando se entrena de cero para evitar overfitting)
          mosaic=True,
          mixup=0.5,
          
          project='runs',
          name='traffic-scratch-y11m',
          exist_ok=True,
      )
    else:
      # FINE-TUNING
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
