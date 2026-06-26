# Deploying on coolify


# Main steps

1. Setup deploy keys for the repo in github, then add them to coolify
2. Create a new project for a private repo in github using deploy keys. Point to main branch and select docker compose as deployment method
3. Enter domains for the app
- minio: siat-minio.unlp.dev:9000
- backend-api: siat-backend.unlp.dev:8000
- frontend: siat.unlp.dev:3000
- backend-worker: localhost
4. Enter env variables for the app
   1. postgres: DB_USER, DB_PASS, DB_NAME, POSTGRES_DB, POSTGRES_USER
   2. minio: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD