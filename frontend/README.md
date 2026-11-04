# SIAT — Frontend

SvelteKit 2 + Svelte 5 + Tailwind CSS 4, servido con `adapter-node`.

## Desarrollo

Con el backend levantado en Docker (`docker compose up -d` desde la raíz del repo):

```bash
npm install
npm run dev
```

La app queda en `http://localhost:5173` con recarga en caliente. Las URLs del backend y de MinIO se leen de `frontend/.env` (`BACKEND_URL`, `MINIO_URL`).

## Verificación

```bash
npm run check   # svelte-check
npm run lint    # prettier + eslint
npm run format  # aplica prettier
```

## Contenedor

El servicio `frontend` de `docker-compose.yaml` corre el build de producción (`node build`) en el puerto 3000. No monta el código, así que para ver cambios hay que reconstruirlo:

```bash
docker compose up -d --build --no-deps frontend
```
