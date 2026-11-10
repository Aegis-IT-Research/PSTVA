# Nmap Module

This module runs Nmap in Docker, parses Nmap XML output, and persists results through a Neo4j-side consumer.

## Key files

- Runtime entrypoints: `modules/tools/nmap/scripts/nmap_scan.py`
- Parser: `modules/tools/nmap/utils/nmap_parser.py`
- Tool payload schema (combined payload): `core/database/neo4j/payloads/models.py`
- Developer docs: `modules/tools/nmap/docs/README.md`

## Why the consumer exists

Nmap produces a stable combined payload (`aegis.v1` with `core` + `network`). A legacy ingester translates that payload into the current DB schema.
If the database schema is redesigned later, switch to the new consumers and keep the combined payload stable.
