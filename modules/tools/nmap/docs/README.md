# Nmap module docs

## What this module does

- Runs Nmap in Docker (`instrumentisto/nmap`).
- Parses Nmap XML output into a structured Python dict/list.
- Wraps that structured output into the combined payload (`aegis.v1` with `core` + `network` sections).
- Persists results to Neo4j via a legacy ingester until the new DB schema is deployed.

## Code map

- Runtime entrypoints (imported by core Celery tasks)
  - `modules/tools/nmap/scripts/nmap_scan.py`
    - `nmap_scan_service(target, scan_type, project_id) -> DockerResult`
    - `nmap_scan_save(result, project_id) -> CombinedPayload` (builds payload)

- Parser (structured output)
  - `modules/tools/nmap/utils/nmap_parser.py`
    - `parse_nmap_output(xml) -> List[host_dict]`

- Tool contract (combined payload)
  - `core/database/neo4j/payloads/models.py`
    - `CombinedPayload`, `CoreSection`, `NetworkSection`

- Legacy ingester (DB mapping to current Neo4j schema)
  - `core/database/neo4j/ingest/legacy_ingesters/legacy_nmap_consumer.py`
    - `ingest_legacy_nmap_payload(payload, db=Neo4jManager) -> summary`

## Tool payload schema

See `core/database/neo4j/payloads/models.py` for the combined payload models.

## How persistence works (design intent)

1. Tool runs and produces raw XML.
2. Tool parses XML into Python structures.
3. Tool wraps parsed data into the combined payload (`aegis.v1`).
4. Legacy ingester translates that payload to the current Neo4j schema.

When Neo4j is redesigned later:
- Switch to the new consumers (core/network/web).
- Keep the combined payload stable so tool code and UI/API stay unchanged.

## Tests

Run only Nmap tests:

- `./.venv/bin/pytest -q modules/tools/nmap/tests`

Smoke tests are gated behind `AEGIS_RUN_SMOKE=1`.
