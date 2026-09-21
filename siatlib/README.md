Los datos de entrenamiento están en la carpeta de drive


Crear entorno virtual para entrenamiento de modelo local
Dentro de la carpeta siatlib/
1. uv venv
2. source .venv/bin/activate
3. uv sync
4. python train.py

Si se desea entrenar desde Colab
1. Convertir archivo a ipynb: jupytext --to notebook train.py
2. !pip install ultralytics antes de ejecutar archivo
