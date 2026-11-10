from __future__ import annotations

from typing import Dict

from core.database.neo4j.neo4j_manager import Neo4jManager
from core.database.neo4j.payloads import CombinedPayload
from core.database.neo4j.ingest.core_consumer import ingest_core_section
from core.database.neo4j.ingest.network_consumer import ingest_network_section
from core.database.neo4j.ingest.web_consumer import ingest_web_section


def ingest_combined_payload(payload: CombinedPayload, *, db: Neo4jManager) -> Dict:
    summary: Dict[str, int | str] = {
        "status": "ingested",
        "schema_version": payload.schema_version,
        "project_id": payload.project_id,
        "run_id": payload.run.id,
    }

    if payload.core is not None:
        core_summary = ingest_core_section(
            payload.core, run=payload.run, project_id=payload.project_id, db=db
        )
        summary.update({f"core_{k}": v for k, v in core_summary.items()})

    if payload.network is not None:
        network_summary = ingest_network_section(
            payload.network, run=payload.run, project_id=payload.project_id, db=db
        )
        summary.update({f"network_{k}": v for k, v in network_summary.items()})

    if payload.web is not None:
        web_summary = ingest_web_section(
            payload.web, run=payload.run, project_id=payload.project_id, db=db
        )
        summary.update({f"web_{k}": v for k, v in web_summary.items()})

    return summary


def persist_combined_payload(payload: CombinedPayload) -> Dict:
    db = Neo4jManager()
    try:
        return ingest_combined_payload(payload, db=db)
    finally:
        db.close()
