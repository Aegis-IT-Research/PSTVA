from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from core.database.neo4j.neo4j_manager import Neo4jManager
from core.database.neo4j.payloads import CombinedPayload, CoreSection, Finding


def _artifact_output(core: Optional[CoreSection]) -> Optional[str]:
    if not core:
        return None
    for artifact in core.artifacts:
        if artifact.raw_text:
            return artifact.raw_text
    return None


def parse_port_target(uid: str, project_id: str) -> Tuple[Optional[str], Optional[int]]:
    if not uid or not uid.startswith(f"{project_id}:"):
        return None, None
    tail = uid[len(project_id) + 1 :]
    parts = tail.rsplit(":", 2)
    if len(parts) != 3:
        return None, None
    host, _proto, port = parts
    try:
        return host, int(port)
    except ValueError:
        return host, None


def parse_url_target(uid: str) -> Tuple[Optional[str], Optional[int]]:
    if not uid:
        return None, None
    url = uid if "://" in uid else f"http://{uid}"
    try:
        parsed = urlparse(url)
    except ValueError:
        if "://" not in uid and ":" in uid and not uid.startswith("["):
            try:
                parsed = urlparse(f"http://[{uid}]")
            except ValueError:
                return None, None
        else:
            return None, None
    host = parsed.hostname or parsed.netloc or None
    scheme = parsed.scheme or "http"
    port = parsed.port or (443 if scheme == "https" else 80)
    return host, port


def _log_action(
    payload: CombinedPayload, *, db: Neo4jManager, action: str
) -> int:
    started_at = payload.run.started_at or payload.emitted_at
    finished_at = payload.run.finished_at or payload.emitted_at
    tool_output = _artifact_output(payload.core)
    command = payload.run.command or payload.run.args
    return db.log_action(
        action=action,
        project=payload.project_id,
        time_started=started_at.isoformat(),
        time_ended=finished_at.isoformat(),
        user="Default",
        command=command,
        tool_output=tool_output,
    )


def _persist_network(payload: CombinedPayload, *, db: Neo4jManager) -> Tuple[int, int]:
    host_count = 0
    service_count = 0

    if not payload.network:
        return host_count, service_count

    for host in payload.network.hosts:
        db.add_host(
            ip=host.id,
            project=payload.project_id,
            state=host.state,
            hostname=host.hostname or "",
            dn=host.domain or "",
            os=None,
        )
        host_count += 1

        for port in host.ports:
            svc = port.service
            cpe_uri = svc.cpe[0].uri if svc and svc.cpe else None
            db.add_net_service(
                ip=host.id,
                portid=port.port,
                protocol=port.proto,
                state=port.state,
                name=svc.name if svc else None,
                product=svc.product if svc else None,
                version=svc.version if svc else None,
                cpe=cpe_uri,
                project=payload.project_id,
            )
            service_count += 1

    return host_count, service_count


def _persist_findings(
    payload: CombinedPayload,
    *,
    db: Neo4jManager,
    target_resolver: Callable[[Finding, str], Tuple[Optional[str], Optional[int]]],
) -> int:
    vuln_count = 0
    if not payload.core:
        return vuln_count

    for finding in payload.core.findings:
        target_ip, target_port = target_resolver(finding, payload.project_id)
        if not target_ip:
            continue

        db.add_vulnerability(
            ip=target_ip,
            portid=target_port,
            vuln=finding.title,
            cvss=finding.cvss,
            link=None,
            exploit=None,
            project=payload.project_id,
        )
        vuln_count += 1

    return vuln_count


def ingest_legacy_payload(
    payload: CombinedPayload,
    *,
    db: Neo4jManager,
    action: str,
    target_resolver: Callable[[Finding, str], Tuple[Optional[str], Optional[int]]],
) -> Dict:
    if not db.check_project_exists(payload.project_id):
        raise ValueError(f"Project with ID '{payload.project_id}' does not exist.")

    log_id = _log_action(payload, db=db, action=action)
    host_count, service_count = _persist_network(payload, db=db)
    vuln_count = _persist_findings(payload, db=db, target_resolver=target_resolver)

    return {
        "status": "ingested",
        "schema_version": payload.schema_version,
        "project_id": payload.project_id,
        "run_id": payload.run.id,
        "log_id": log_id,
        "hosts": host_count,
        "services": service_count,
        "vulnerabilities": vuln_count,
    }
