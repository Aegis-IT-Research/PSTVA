from datetime import datetime
import ast
import re
from typing import List, Tuple
from urllib.parse import urlparse
from uuid import uuid4

from modules.tools.nikto.resolvers.nikto_resolver import resolve_nikto_command
from core.infra.app.docker_manager import DockerManager, DockerResult
from core.database.neo4j.payloads import (
    Artifact,
    CombinedPayload,
    CoreSection,
    Finding,
    FindingTarget,
    NetworkHost,
    NetworkPort,
    NetworkSection,
    NetworkService,
    RunMeta,
    WebSection,
    WebSite,
)
from core.database.neo4j.neo4j_manager import Neo4jManager


def nikto_scan_service(target: str, scan_type: str, project_id: str) -> DockerResult:
    cmd_list = resolve_nikto_command(scan_type, target).split(" ")

    db = Neo4jManager()

    if not db.check_project_exists(project_id):
        raise ValueError(f"Project with ID '{project_id}' does not exist.")

    manager = DockerManager()
    result = manager.run("frapsoft/nikto", cmd_list)

    db.close()
    return result


def nikto_scan_save(
    docker_result: DockerResult,
    project_id: str,
    scan_type: str = "default",
    run_id: str | None = None,
):
    return nikto_build_combined_payload(
        docker_result,
        project_id=project_id,
        scan_type=scan_type,
        run_id=run_id or str(uuid4()),
    )


def _normalize_key(val: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", val.strip().lower())
    return cleaned.strip("_") or "finding"


def _clean_target(value: str) -> str:
    cleaned = value.strip()
    if (cleaned.startswith("'") and cleaned.endswith("'")) or (
        cleaned.startswith('"') and cleaned.endswith('"')
    ):
        cleaned = cleaned[1:-1]
    cleaned = cleaned.rstrip(",")
    # Strip list artifacts but keep bracketed IPv6.
    if "://" not in cleaned:
        if cleaned.startswith("[") and cleaned.endswith("]") and ":" in cleaned:
            return cleaned
        if cleaned.endswith("]"):
            cleaned = cleaned[:-1]
        if cleaned.startswith("["):
            cleaned = cleaned[1:]
    return cleaned


def _infer_target(command: str) -> str:
    cmd = command.strip()
    if cmd.startswith("[") and cmd.endswith("]"):
        try:
            parts = ast.literal_eval(cmd)
            if isinstance(parts, list) and parts:
                for i, part in enumerate(parts):
                    if part == "-h" and i + 1 < len(parts):
                        return _clean_target(str(parts[i + 1]))
                return _clean_target(str(parts[-1]))
        except Exception:
            pass

    cmd_parts = cmd.split()
    for i, part in enumerate(cmd_parts):
        if part == "-h" and i + 1 < len(cmd_parts):
            return _clean_target(cmd_parts[i + 1])
    return _clean_target(cmd_parts[-1]) if len(cmd_parts) > 1 else _clean_target(cmd)


def _parse_base_url(target: str, scan_type: str) -> Tuple[str, str]:
    if target.startswith("http://") or target.startswith("https://"):
        parsed = urlparse(target)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or parsed.netloc or target
        port = parsed.port
        if port:
            return f"{scheme}://{host}:{port}", scheme
        return f"{scheme}://{host}", scheme
    scheme = "https" if scan_type.lower() == "ssl" else "http"
    return f"{scheme}://{target}", scheme


def nikto_build_combined_payload(
    result: DockerResult,
    *,
    project_id: str,
    scan_type: str,
    run_id: str,
) -> CombinedPayload:
    output = result.logs
    host, ip, port, banner, vulnerabilities = parse_nikto_output(output)

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
        tool="nikto",
        version=None,
        args=result.command,
        command=result.command,
        started_at=started_at,
        finished_at=ended_at,
        exit_code=None,
    )

    artifacts = [
        Artifact(
            id=f"{run_id}:nikto_txt",
            kind="nikto_txt",
            created_at=ended_at or datetime.utcnow(),
            raw_text=output,
            size_bytes=len(output or ""),
            truncated=False,
        )
    ]

    target = _infer_target(result.command)
    base_url, scheme = _parse_base_url(target or host or ip, scan_type)

    host_id = ip or host or target
    port_num = int(port) if port and str(port).isdigit() else (443 if scheme == "https" else 80)
    port_uid = f"{project_id}:{host_id}:tcp:{port_num}"
    service_name = banner or scheme
    service = NetworkService(
        uid=f"{port_uid}:{service_name}",
        name=service_name,
        product=banner or None,
        version=None,
        protocol="tcp",
        state="open",
        port=port_num,
        first_seen=started_at,
        last_seen=ended_at,
    )
    network = NetworkSection(
        hosts=[
            NetworkHost(
                id=host_id,
                state="up",
                hostname=host or "",
                domain=None,
                created_at=started_at,
                last_seen=ended_at,
                ports=[
                    NetworkPort(
                        uid=port_uid,
                        proto="tcp",
                        port=port_num,
                        state="open",
                        first_seen=started_at,
                        last_seen=ended_at,
                        service=service,
                    )
                ],
            )
        ]
    )

    findings: list[Finding] = []
    for uri, ref, description in vulnerabilities:
        norm = _normalize_key(description)
        finding_uid = f"{project_id}:{host_id}:{port_num}:{norm}"
        target_uid = f"{base_url}{uri}" if uri else base_url
        findings.append(
            Finding(
                uid=finding_uid,
                title=description,
                severity="Medium",
                category="web",
                cve=None,
                cvss=None,
                status="open",
                first_seen=ended_at or datetime.utcnow(),
                last_seen=ended_at or datetime.utcnow(),
                target=FindingTarget(type="url", uid=target_uid),
            )
        )

    core = CoreSection(artifacts=artifacts, findings=findings, evidence=[])

    web = WebSection(
        websites=[
            WebSite(
                uid=base_url,
                scheme=scheme,
                first_seen=started_at,
                last_seen=ended_at,
            )
        ]
    )

    return CombinedPayload(
        project_id=project_id,
        run=run,
        core=core,
        network=network,
        web=web,
    )


def parse_nikto_output(output):
    host = ""
    ip = ""
    port = ""
    banner = ""
    vulnerabilities = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("+ Target IP:"):
            ip = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("+ Target Hostname:"):
            host = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("+ Target Port:"):
            port = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("+ Server:"):
            banner = stripped.split(":", 1)[1].strip()

        if not stripped.startswith("+ ") or any(
            stripped.startswith(x)
            for x in [
                "+ Target",
                "+ Server",
                "+ Start Time",
                "+ End Time",
                "+ 1 host(s) tested",
            ]
        ):
            continue

        description = stripped[2:].strip()

        uri = "/"
        m = re.search(r"(/[^ :]+)(?::|\s|$)", description)
        if m:
            uri = m.group(1)

        ref = ""
        m2 = re.search(r"(https?://[^\s]+)", description)
        if m2:
            ref = m2.group(0)
        v = [uri, ref, description]
        vulnerabilities.append(v)

    return host, ip, port, banner, vulnerabilities


def scan_nikto(target: str, args: List[str], project: str):
    result = nikto_scan_service(target, args, project)
    summary = nikto_scan_save(result, project)
    return summary
