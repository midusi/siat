#!/bin/sh
# start minio server
minio server /data --console-address ":9001" &

# wait a few seconds para que levante
sleep 5

# configura alias
mc alias set localminio http://127.0.0.1:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# crea el bucket si no existe
mc mb --ignore-existing localminio/siat

# aplica CORS
mc cors set localminio/siat /minio-init/minio-cors.json

# espera al proceso principal
wait
echo "MinIO initialization completed."