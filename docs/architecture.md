## 🏗️ 

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Network                          │
│                   (siat_network)                         │
│                                                             │
│  ┌──────────┐         ┌─────────────┐       ┌──────────┐    │
│  │PostgreSQL│◄────────┤ Backend API │◄──────┤ Frontend │    │
│  │   (db)   │         │  (API only) │       │ (SSR)    │    │
│  │ Port:    │         │ Port: 8000  │       │ Port:    │    │
│  │  5432    │         │  (internal) │       │  3000    │◄───┼─┐ Users
│  └──────────┘         └──────┬──────┘       └────┬─────┘    │ │
│       ▲                      │                    │         │ │
│       │                      │                    │         │ │
│       │                      ▼                    ▼         │ │
│       │              ┌────────────┐       ┌──────────┐      │ │
│       │              │   MinIO    │◄──────┤  MinIO   │──────┼─┘
│       │              │  Storage   │       │ Console  │      │
│       │              │ Port: 9000 │       │Port: 9001│◄─────┼─── Admins
│       │              └──────▲─────┘       └──────────┘      │
│       │                     │                               │
│       │                     │                               │
│       │              ┌──────┴───────┐                       │
│       └──────────────┤Backend Worker│                       │
│                      │  (Inference) │                       │
│                      │  GPU Support │                       │
│                      └──────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

### Volúmenes Persistentes:
- postgres_data: Base de datos
- minio_data: Videos y resultados
- model_weights: Modelo YOLO compartido



```