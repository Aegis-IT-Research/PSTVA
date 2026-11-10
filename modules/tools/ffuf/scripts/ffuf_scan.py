import os
from urllib.parse import urlparse

import docker

from core.app.docker_runner import DockerManager, DockerResult
from core.database.neo4j.neo4j_manager import Neo4jManager
from modules.tools.ffuf.resolvers.ffuf_resolver import resolve_ffuf_command
from modules.tools.ffuf.utils.ffuf_parser import parse_ffuf_output

FFUF_IMAGE = "ffuf-tool:latest"
DOCKER_CONTEXT = os.path.join(os.path.dirname(__file__), "..", "docker")


def ensure_image():
    cli = docker.from_env()
    try:
        cli.images.get(FFUF_IMAGE)
    except docker.errors.ImageNotFound:
        cli.images.build(path=os.path.abspath(DOCKER_CONTEXT), tag=FFUF_IMAGE, rm=True)


def ffuf_scan_service(target: str, scan_type: str, project_id: str) -> DockerResult:
    db = Neo4jManager()
    try:
        if not db.check_project_exists(project_id):
            raise ValueError(f"Project with ID '{project_id}' does not exist.")
    finally:
        db.close()

    command = resolve_ffuf_command(scan_type, target)
    ensure_image()
    return DockerManager().run_container(image=FFUF_IMAGE, command=command, remove=True)


def ffuf_scan_save(docker_result: DockerResult, project_id: str, target: str) -> dict:
    url = urlparse(target)
    port = url.port or (443 if url.scheme == "https" else 80)
    hits = parse_ffuf_output(docker_result.logs)

    db = Neo4jManager()
    try:
        db.log_action(
            action="ffuf scan",
            project=project_id,
            time_started=docker_result.start_time,
            time_ended=docker_result.end_time,
            user="system",
            command=docker_result.command,
            tool_output=docker_result.logs,
        )
        for hit in hits:
            db.add_web_path(
                ip=url.hostname, portid=port, scheme=url.scheme, url=hit["url"],
                status=hit["status"], length=hit["length"], project=project_id,
            )
    finally:
        db.close()
    return {"status": "ok", "count": len(hits)}
