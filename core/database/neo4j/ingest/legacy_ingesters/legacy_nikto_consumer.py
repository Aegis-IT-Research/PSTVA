from __future__ import annotations

from typing import Dict, Optional, Tuple

from core.app.docker_runner import DockerResult
from core.database.neo4j.neo4j_manager import Neo4jManager
from core.database.neo4j.payloads import CombinedPayload, Finding
from core.database.neo4j.ingest.legacy_ingesters.legacy_base import (
    ingest_legacy_payload,
    parse_port_target,
    parse_url_target,
)


def _resolve_nikto_target(
    finding: Finding, project_id: str
) -> Tuple[Optional[str], Optional[int]]:
    if finding.target:
        if finding.target.type in {"url", "website"}:
            return parse_url_target(finding.target.uid)
        if finding.target.type == "host":
            return finding.target.uid, None
        if finding.target.type == "port":
            return parse_port_target(finding.target.uid, project_id)
    return None, None


def ingest_legacy_nikto_payload(payload: CombinedPayload, *, db: Neo4jManager) -> Dict:
    """Persist Nikto combined payload into the legacy Neo4j model."""

    return ingest_legacy_payload(
        payload,
        db=db,
        action="nikto scan",
        target_resolver=_resolve_nikto_target,
    )


def persist_legacy_nikto_payload(payload: CombinedPayload) -> dict:
    db = Neo4jManager()
    try:
        return ingest_legacy_nikto_payload(payload, db=db)
    finally:
        db.close()


def log_legacy_nikto_failure(
    *,
    project_id: str,
    docker_result: DockerResult,
    action: str,
    error: str,
) -> dict:
    db = Neo4jManager()
    try:
        log_id = db.log_action(
            action=action,
            project=project_id,
            time_started=docker_result.start_time,
            time_ended=docker_result.end_time,
            user="Default",
            command=docker_result.command,
            tool_output=f"{error}\nRaw output preview: {docker_result.logs[:500]}",
        )
        return {
            "status": "error",
            "reason": action,
            "log_id": log_id,
            "project_id": project_id,
        }
    finally:
        db.close()
