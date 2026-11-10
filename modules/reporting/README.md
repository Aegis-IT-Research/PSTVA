# Reporting Module (Scaffold)

This folder is the target location for report generation as the repo structure evolves.

## Current state

- The report builder image is currently defined under `modules/reporting/reportbuilder/docker/`.
- Report scripts/templates live under `modules/reporting/`.
- Runtime code builds/runs the image tagged `pentest-report-builder:latest`.

## Build (transitional)

From repo root:

- `make build-reporting-mod`

This builds using:

- Dockerfile: `modules/reporting/reportbuilder/docker/Dockerfile`
- Build context: `app/`

Later we can move these into `modules/reporting/` without changing the image contract.
