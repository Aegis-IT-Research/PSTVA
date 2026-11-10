# PSTVA – Module Documentation Index

This file is the entry-point for documentation that is **owned by each module** under `modules/`.

## Core (always present)

- Backend runtime (FastAPI/Celery): [core/app](../core/app)
- Neo4j integration and consumers: [core/database/neo4j](../core/database/neo4j)
- Infrastructure (Compose/Traefik): [core/infra](../core/infra)

## Modules

### Frontend

- Module README: [modules/frontend/README.md](../modules/frontend/README.md)
- React app (Create React App): [modules/frontend/app](../modules/frontend/app)

### Reporting

- Module README: [modules/reporting/README.md](../modules/reporting/README.md)
- Templates/runtime/scripts: [modules/reporting](../modules/reporting)

### Tools

- Tools overview: [modules/tools/README.md](../modules/tools/README.md)

#### Nmap

- Module README: [modules/tools/nmap/README.md](../modules/tools/nmap/README.md)
- Developer docs: [modules/tools/nmap/docs/README.md](../modules/tools/nmap/docs/README.md)

#### Nikto

- Module README: [modules/tools/nikto/README.md](../modules/tools/nikto/README.md)

#### ADEnum

- Module README: [modules/tools/adenum/README.md](../modules/tools/adenum/README.md)

#### Kerbrute

- Module README: [modules/tools/kerbrute/README.md](../modules/tools/kerbrute/README.md)

#### FFuF

- Module README: [modules/tools/ffuf/README.md](../modules/tools/ffuf/README.md)

#### Horusec

- Module README: [modules/tools/horusec/README.md](../modules/tools/horusec/README.md)

## Conventions

- Each module owns its documentation in its own folder (at minimum a `README.md`).
- Tool/database decoupling pattern:
  - Tools emit a stable, tool-specific payload (example: `nmap.v1`).
  - Persistence happens via a DB-side consumer under [core/database/neo4j/ingest](../core/database/neo4j/ingest).
  - When Neo4j schema changes, update the consumer mapping without changing the tool payload.
