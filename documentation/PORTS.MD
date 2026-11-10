# Port Inventory

This document lists ports used by this repository, what they are used for, and where they are configured.

## Host-Exposed Ports (Loopback)

These ports are published on `127.0.0.1` (local machine only) by Docker Compose.

| Port | Protocol | Purpose | Config Source |
|---|---|---|---|
| `80` | TCP | Main HTTP entrypoint served by Traefik (`web` entrypoint). Routes to frontend (`/`) and backend (`/back`). | `core/infra/compose.yml`, `core/infra/compose.core.yml`, `core/infra/traefik.yml` |
| `8080` | TCP | Traefik dashboard/API (`api.insecure: true`). | `core/infra/compose.yml`, `core/infra/compose.core.yml`, `core/infra/compose.openports.yml`, `core/infra/traefik.yml` |
| `7474` | TCP | Neo4j HTTP interface. | `core/infra/compose.yml`, `core/infra/compose.core.yml`, `core/infra/compose.openports.yml` |
| `7687` | TCP | Neo4j Bolt protocol (database driver connections). | `core/infra/compose.yml`, `core/infra/compose.core.yml`, `core/infra/compose.openports.yml`, `core/database/neo4j/neo4j_manager.py` |
| `8000` | TCP | Backend FastAPI/Uvicorn direct access when `compose.openports` overlay is enabled. | `core/infra/compose.openports.yml`, `core/infra/app/manage.sh`, `core/Dockerfile` |
| `3000` | TCP | Frontend direct access when `compose.openports` overlay is enabled (dev-style mapping). | `core/infra/compose.openports.yml` |

## Internal Container/Network Ports

These are used between services on the Docker network and are not published by default to the host.

| Port | Protocol | Purpose | Config Source |
|---|---|---|---|
| `8000` | TCP | Backend API process (Uvicorn inside `back` container). Traefik forwards `/back` traffic to this port. | `core/infra/app/manage.sh`, `core/Dockerfile`, `core/infra/compose.yml`, `core/infra/compose.core.yml` |
| `80` | TCP | Frontend Nginx inside `front` container. Traefik forwards root host traffic to this port. | `modules/frontend/app/nginx.conf`, `core/infra/compose.yml`, `core/infra/compose.modules.yml` |
| `5555` | TCP | Flower UI for Celery monitoring, routed by Traefik under `/flower`. | `core/infra/compose.yml`, `core/infra/compose.modules.yml`, `core/infra/app/manage.sh` |
| `6379` | TCP | Redis broker/result backend for Celery (`db 0` broker, `db 1` backend). | `core/infra/compose.yml`, `core/infra/compose.core.yml`, `core/app/tasks.py`, `core/infra/scripts/list_celery_jobs.py` |


## Notes

- The default startup paths (`make start`, `make start-core`) expose only loopback-bound ports (`127.0.0.1`), not all interfaces.
- `make start-core-open` adds direct host access mappings using `core/infra/compose.openports.yml`.
- Traefik is the main ingress point; backend/frontend/flower are primarily reached through Traefik routing on port `80`.
