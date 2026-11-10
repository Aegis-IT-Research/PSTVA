# Frontend Module (Scaffold)

This folder is the target location for the React frontend as the repo structure evolves.

## Current state

- The frontend code lives under `modules/frontend/app/`.
- Docker Compose still references the same `${FRONT_END_IMAGE}` tag.

## Build

From the repo root:

- `make build-front-mod`

This builds from `modules/frontend/app/`.
