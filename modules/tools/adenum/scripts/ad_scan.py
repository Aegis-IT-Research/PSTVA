import shlex
import argparse
import docker
import os

from core.infra.app.docker_manager import DockerManager, DockerResult
from modules.tools.adenum.utils.ad_scan_parser import parse_adenum_output, strip_ansi
from core.database.neo4j.neo4j_manager import Neo4jManager


ADENUM_IMAGE = "adenum-suite"
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
DOCKER_CONTEXT = os.path.join(REPO_ROOT, "modules", "tools", "adenum", "docker")
DOCKERFILE_PATH = "Dockerfile"


def adenum_scan_service(target: str, args: list, project: str) -> DockerResult:
    """Runs ADenum in Docker and captures all output + timings in a DockerResult."""
    adenum_image()

    manager = DockerManager()
    raw = manager.run("adenum-suite", args)

    return raw


def adenum_scan_save(docker_result: DockerResult, project_id: str) -> dict:
    db = Neo4jManager()
    try:
        if not db.check_project_exists(project_id):
            raise ValueError(f"Project '{project_id}' not found")

        log_id = db.log_action(
            action="adenum scan",
            project=project_id,
            time_started=docker_result.start_time,
            time_ended=docker_result.end_time,
            user="Default",
            command=docker_result.command,
            tool_output=docker_result.logs,
        )

        cmd_parts = docker_result.command.split()
        domain = ""
        dc_ip = ""

        for i, part in enumerate(cmd_parts):
            if part == "-d" and i + 1 < len(cmd_parts):
                domain = cmd_parts[i + 1]
            elif part == "-ip" and i + 1 < len(cmd_parts):
                dc_ip = cmd_parts[i + 1]

        cleaned = "\n".join(
            l
            for l in strip_ansi(docker_result.logs).splitlines()
            if l.strip() and not l.strip().startswith(("█", "═"))
        )
        parsed = parse_adenum_output(cleaned)

        parsed_ip = parsed.get("ip") or dc_ip

        host_count = 0
        for controller in parsed.get("domainControllers", []):
            db.add_host(
                ip=dc_ip,
                project=project_id,
                state="active",
                hostname=controller.get("name"),
                dn=controller.get("dn"),
                os=controller.get("os", ""),
            )
            host_count += 1

        user_count = 0
        for user in parsed.get("users", []):
            db.add_user(
                username=user["username"],
                dn=user.get("dn"),
                roles=user.get("roles", []),
                host_ip=dc_ip,
                project=project_id,
            )
            user_count += 1

        return {
            "log_id": log_id,
            "hosts": host_count,
            "users": user_count,
            "domain": domain,
            "dc_ip": dc_ip,
            "parsed_ip": parsed_ip,
        }

    finally:
        db.close()


def adenum_image():
    cli = docker.from_env()
    abs_dockerfile_path = os.path.join(DOCKER_CONTEXT, DOCKERFILE_PATH)
    print(f"[DEBUG] Docker context: {DOCKER_CONTEXT}")
    print(f"[DEBUG] Dockerfile path: {abs_dockerfile_path}")

    try:
        cli.images.get(ADENUM_IMAGE)
    except docker.errors.ImageNotFound:
        print("[+] Building adenum-suite image …")
        cli.images.build(
            path=DOCKER_CONTEXT, dockerfile=DOCKERFILE_PATH, tag=ADENUM_IMAGE, rm=True
        )
        print("[+] Build complete")


def parse_ui_input(cmd: str) -> dict:
    p = argparse.ArgumentParser()
    p.add_argument("-d", required=True)
    p.add_argument("-ip", required=True)
    p.add_argument("-u", required=True)
    p.add_argument("-p", required=True)
    p.add_argument("-j", action="store_true")
    p.add_argument("-w", default="/opt/wordlists/rockyou.txt")
    p.add_argument("--extra", default="")
    a = p.parse_args(shlex.split(cmd))
    return {
        "domain": a.d,
        "dc_ip": a.ip,
        "username": a.u,
        "password": a.p,
        "enable_john": a.j,
        "wordlist": a.w,
        "extra": a.extra,
    }
