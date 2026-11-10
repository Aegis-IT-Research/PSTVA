from datetime import datetime
import re
from uuid import uuid4

from modules.tools.nmap.resolvers.nmap_resolver import resolve_nmap_command
from core.infra.app.docker_manager import DockerManager, DockerResult
from core.database.neo4j.payloads import (
    Artifact,
    CombinedPayload,
    CoreSection,
    Finding,
    FindingTarget,
    NetworkCPE,
    NetworkHost,
    NetworkPort,
    NetworkSection,
    NetworkService,
    RunMeta,
)
from modules.tools.nmap.utils.nmap_parser import parse_nmap_output


def nmap_scan_service(target, scan_type: str, project_id: str, run_id: str | None = None):
    """Run Nmap in Docker and return raw output (XML) wrapped in DockerResult."""
    resolved = resolve_nmap_command(scan_type, target).split()
    if resolved and resolved[0].lower() == "nmap":
        resolved = resolved[1:]
    if "-oX" not in resolved:
        resolved += ["-oX", "-"]

    manager = DockerManager()
    return manager.run("instrumentisto/nmap", resolved)


def _cvss_to_severity(cvss_val: str | None) -> str:
    try:
        v = float(cvss_val) if cvss_val is not None and cvss_val != "-" else None
    except ValueError:
        v = None
    if v is None:
        return "Informational"
    if v >= 9.0:
        return "Critical"
    if v >= 7.0:
        return "High"
    if v >= 4.0:
        return "Medium"
    if v > 0.0:
        return "Low"
    return "Informational"


def _normalize_key(val: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", val.strip().lower())
    return cleaned.strip("_") or "finding"


def nmap_build_combined_payload(
    result: DockerResult,
    *,
    project_id: str,
    scan_type: str,
    run_id: str,
) -> CombinedPayload:
    """Pure transformation: raw Nmap XML -> combined core/network payload."""

    parsed_hosts = parse_nmap_output(result.logs)

    started_at = None
    ended_at = None
    try:
        if result.start_time:
            started_at = datetime.fromisoformat(result.start_time)
        if result.end_time:
            ended_at = datetime.fromisoformat(result.end_time)
    except Exception:
        started_at = None
        ended_at = None

    run = RunMeta(
        id=run_id,
        tool="nmap",
        version=None,
        args=result.command,
        command=result.command,
        started_at=started_at,
        finished_at=ended_at,
        exit_code=None,
    )

    artifact_id = f"{run_id}:nmap_xml"
    artifacts = [
        Artifact(
            id=artifact_id,
            kind="nmap_xml",
            created_at=ended_at or datetime.utcnow(),
            raw_text=result.logs,
            size_bytes=len(result.logs or ""),
            truncated=False,
        )
    ]

    findings: list[Finding] = []
    network_hosts: list[NetworkHost] = []

    for host in parsed_hosts:
        host_id = host.get("ip")
        host_state = host.get("state")
        hostname = host.get("hostname") or ""
        domain = host.get("domain") or ""

        port_proto_map = {
            str(s.get("portid")): s.get("protocol") for s in host.get("services", [])
        }

        ports: list[NetworkPort] = []
        for svc in host.get("services", []):
            if svc.get("portid") is None:
                continue
            portid = int(svc.get("portid"))
            proto = svc.get("protocol") or "tcp"
            state = svc.get("state") or "unknown"
            port_uid = f"{project_id}:{host_id}:{proto}:{portid}"
            svc_name = svc.get("name") or ""
            svc_uid = f"{port_uid}:{svc_name}" if svc_name else port_uid
            cpe_val = svc.get("cpe") or ""
            cpes = [NetworkCPE(uri=cpe_val)] if cpe_val else []
            service = NetworkService(
                uid=svc_uid,
                name=svc_name or "unknown",
                product=svc.get("product") or None,
                version=svc.get("version") or None,
                protocol=proto,
                state=state,
                port=portid,
                first_seen=started_at,
                last_seen=ended_at,
                cpe=cpes,
            )
            ports.append(
                NetworkPort(
                    uid=port_uid,
                    proto=proto,
                    port=portid,
                    state=state,
                    first_seen=started_at,
                    last_seen=ended_at,
                    service=service,
                )
            )

        network_hosts.append(
            NetworkHost(
                id=host_id,
                state=host_state,
                hostname=hostname,
                domain=domain,
                created_at=started_at,
                last_seen=ended_at,
                ports=ports,
            )
        )

        for v in host.get("vulnerabilities", []):
            vuln_title = v.get("vulnerability") or "Unspecified Vulnerability"
            cvss_val = v.get("cvss")
            portid = v.get("portid")
            proto = port_proto_map.get(str(portid), "tcp") if portid else None
            if portid and proto:
                target_uid = f"{project_id}:{host_id}:{proto}:{portid}"
                target_type = "port"
            else:
                target_uid = host_id
                target_type = "host"

            norm = _normalize_key(vuln_title)
            finding_uid = (
                f"{project_id}:{host_id}:{portid or 'host'}:{norm}"
            )

            cve_val = vuln_title if vuln_title.upper().startswith("CVE-") else None
            findings.append(
                Finding(
                    uid=finding_uid,
                    title=vuln_title,
                    severity=_cvss_to_severity(cvss_val),
                    category="network",
                    cve=cve_val,
                    cvss=float(cvss_val) if cvss_val not in (None, "", "-") else None,
                    status="open",
                    first_seen=ended_at or datetime.utcnow(),
                    last_seen=ended_at or datetime.utcnow(),
                    target=FindingTarget(type=target_type, uid=target_uid),
                )
            )

    core = CoreSection(artifacts=artifacts, findings=findings, evidence=[])
    network = NetworkSection(hosts=network_hosts)

    return CombinedPayload(
        project_id=project_id,
        run=run,
        core=core,
        network=network,
        web=None,
    )


def nmap_scan_save(result: DockerResult, project_id: str, run_id: str | None = None):
    """Backward-compatible shim.

    This used to persist to Neo4j. It now returns the Nmap tool payload.
    """
    return nmap_build_combined_payload(
        result,
        project_id=project_id,
        scan_type="unknown",
        run_id=run_id or str(uuid4()),
    )
