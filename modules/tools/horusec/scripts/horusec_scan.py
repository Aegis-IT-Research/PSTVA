from core.app.docker_runner import DockerManager, DockerResult
from modules.tools.horusec.models.horusec_scan import HorusecScanDTO
from modules.tools.horusec.utils.horusec_parser import parse_horusec_output, HorusecParseError
from modules.tools.horusec.resolvers.horusec_resolver import resolve_horusec_command
from core.database.neo4j.neo4j_manager import Neo4jManager
import os
import zipfile
import shutil
from uuid import uuid4


HORUSEC_IMAGE = "horuszup/horusec-cli:latest"
BASE_WORKDIR = "/tmp/curium/horusec"


def prepare_workspace(payload: HorusecScanDTO, project_id: str) -> str:
    workspace = os.path.join(BASE_WORKDIR, project_id)

    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    os.makedirs(workspace, exist_ok=True)

    if not payload.source or not os.path.isfile(payload.source):
        raise ValueError("ZIP source path is invalid or missing")

    with zipfile.ZipFile(payload.source, "r") as zip_ref:
        zip_ref.extractall(workspace)

    try:
        os.remove(payload.source)
    except OSError:
        pass

    return workspace

def horusec_scan_service(payload: HorusecScanDTO, project_id: str) -> DockerResult:
    """
    Runs Horusec scan inside Docker and returns DockerResult.
    """

    db = Neo4jManager()

    if not db.check_project_exists(project_id):
        db.close()
        raise ValueError(f"Project '{project_id}' does not exist")
    
    workspace_path = prepare_workspace(payload, project_id)

    command = resolve_horusec_command(payload)

    volumes = {
        workspace_path: {
            "bind": "/workspace",
            "mode": "rw",
        },
    }

    manager = DockerManager()
    result = manager.run_container(
        image=HORUSEC_IMAGE,
        command=command,
        volumes=volumes,
        remove=True,
    )

    db.close()
    return result


def horusec_scan_save(result: DockerResult, project_id: str):
    """
    Parses Horusec output and stores vulnerabilities in Neo4j.
    """

    db = Neo4jManager()

    scan_id = str(uuid4())

    db.create_scan(
        project_id=project_id,
        scan={
            "id": scan_id,
            "tool": "horusec",
            "started_at": result.start_time,
            "finished_at": result.end_time,
            "status": "completed",
        }
    )

    db.log_action(
        action="horusec scan",
        project=project_id,
        time_started=result.start_time,
        time_ended=result.end_time,
        user="system",
        command=result.command,
        tool_output=result.logs,
    )

    workspace_path = os.path.join(BASE_WORKDIR, project_id)
    json_path = os.path.join(workspace_path, "horusec-result.json")

    if not os.path.isfile(json_path):
        db.log_action(
        action="horusec json missing",
        project=project_id,
        time_started=result.start_time,
        time_ended=result.end_time,
        user="system",
        command=result.command,
        tool_output=f"Expected at {json_path}, files: {os.listdir(workspace_path)}",
        )
        db.close()
        return {"status": "error", "reason": "horusec json file not found"}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            json_content = f.read()

        parsed = parse_horusec_output(json_content)

    except (HorusecParseError, OSError) as e:
        db.log_action(
            action="horusec parse error",
            project=project_id,
            time_started=result.start_time,
            time_ended=result.end_time,
            user="system",
            command=result.command,
            tool_output=str(e),
        )
        db.close()
        return {"status": "error", "reason": "parse failed"}

    for vuln in parsed.get("vulnerabilities", []):
        db.add_code_vulnerability(
            project=project_id,
            scan_id=scan_id,
            tool="horusec",
            severity=vuln.get("severity"),
            confidence=vuln.get("confidence"),
            rule=vuln.get("rule_id"),
            file=vuln.get("file"),
            line=vuln.get("line"),
            column=vuln.get("column"),
            code=vuln.get("code"),
            details=vuln.get("details"),
            hash=vuln.get("vuln_hash"),
        )

    db.close()
    return {
        "status": "ok",
        "count": len(parsed.get("vulnerabilities", [])),
    }