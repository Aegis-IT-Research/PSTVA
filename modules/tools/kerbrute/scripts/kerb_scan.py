import shlex
import argparse
import re
import docker
import os

from modules.tools.kerbrute.resolvers.kerb_resolver import resolve_kerb_command
from core.infra.app.docker_manager import DockerManager, DockerResult

from typing import List
from modules.tools.kerbrute.models.kerb_scan import KerbScanDTO
from modules.tools.kerbrute.utils.kerb_parser import kerbscan_parse_output


KERBRUTE_IMAGE = "kerbrute-tool:latest"
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
DOCKER_CONTEXT = os.path.join(REPO_ROOT, "modules", "tools", "kerbrute", "docker")
DOCKERFILE_PATH = "Dockerfile"


def kerbrute_scan_service(request: KerbScanDTO) -> DockerResult:
    from core.database.neo4j.neo4j_manager import Neo4jManager

    db = Neo4jManager()

    kerbrute_command = resolve_kerb_command(request)
    cfg = parse_ui_input(kerbrute_command)
    args = build_kerbrute_args(cfg)

    if not db.check_project_exists(request.project):
        raise ValueError(f"Project with ID '{request.project}' does not exist.")

    ensure_image()

    manager = DockerManager()
    result = manager.run_container(
        image=KERBRUTE_IMAGE, command=args, remove=True, network_mode="host"
    )

    db.close()
    return result


def kerbrute_scan_save(docker_result: DockerResult, project_id: str) -> dict:
    from core.database.neo4j.neo4j_manager import Neo4jManager

    db = Neo4jManager()
    try:
        if not db.check_project_exists(project_id):
            raise ValueError(f"Project '{project_id}' not found")

        log_id = db.log_action(
            action="kerbrute scan",
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
        subcommand = ""

        for i, part in enumerate(cmd_parts):
            if part in ["userenum", "passwordspray", "bruteuser"]:
                subcommand = part
            elif part == "--domain" and i + 1 < len(cmd_parts):
                domain = cmd_parts[i + 1]
            elif part == "--dc" and i + 1 < len(cmd_parts):
                dc_ip = cmd_parts[i + 1]

        parsed_data = kerbscan_parse_output(docker_result.logs)

        kdcs = parsed_data["kdcs"]
        logins = parsed_data["logins"]

        state = "active" if dc_ip or kdcs else "inactive"

        for kdc in kdcs:
            db.add_host(
                ip=kdc["server"],
                project=project_id,
                state="active",
                hostname=f"{domain} KDC (Port {kdc['port']})",
                dn=domain,
                os=None,
            )

        target_host = dc_ip or (kdcs[0]["server"] if kdcs else None)

        login_count = 0
        for login_data in logins:
            db.add_user(
                username=login_data["username"],
                dn=login_data["full_username"],
                roles=["Kerbrute Valid Login"],
                host_ip=target_host,
                project=project_id,
            )
            login_count += 1

        return {
            "log_id": log_id,
            "logins": login_count,
            "valid_logins": logins,
            "kdcs": kdcs,
            "domain": domain,
            "dc_ip": dc_ip,
            "target_host": target_host,
            "subcommand": subcommand,
            "state": state,
        }

    finally:
        db.close()


def scan_kerbrute(target: str, args: List[str], project: str):
    result = kerbrute_scan_service(target, args, project)
    summary = kerbrute_scan_save(result, project)
    return summary


def ensure_image():
    cli = docker.from_env()
    abs_path = os.path.join(DOCKER_CONTEXT, DOCKERFILE_PATH)
    print("Build context exists:", os.path.isdir(DOCKER_CONTEXT))
    print("Dockerfile exists:", os.path.isfile(abs_path))
    try:
        cli.images.get(KERBRUTE_IMAGE)
    except docker.errors.ImageNotFound:
        print("[+] Building kerbrute image …")
        cli.images.build(
            path=DOCKER_CONTEXT, dockerfile=DOCKERFILE_PATH, tag=KERBRUTE_IMAGE, rm=True
        )
        print("[+] Build complete")


VALID_RE = re.compile(r"VALID USERNAME:\s*(?:[^\s\\]+\\)?(\S+)", re.I)


def extract_valid_users(output: str) -> list[str]:
    clean_output = re.sub(r"\x1B[@-_][0-?]*[ -/]*[@-~]", "", output)
    return [m.group(1) for m in VALID_RE.finditer(clean_output)]


def parse_ui_input(cmd: str) -> dict:
    tokens = shlex.split(cmd)
    subcmds = {"userenum", "passwordspray", "bruteuser"}
    sub = "userenum"
    if tokens and tokens[0].lower() in subcmds:
        sub = tokens.pop(0).lower()
    p = argparse.ArgumentParser()
    p.add_argument("-d", "--domain", required=True, help="Active Directory domain")
    p.add_argument("--dc", help="Domain controller IP")
    p.add_argument("-u", "--userlist", help="Username or userlist file", required=False)
    p.add_argument(
        "-P",
        "--passwordlist",
        help="Passwordlist file or single password",
        required=False,
    )
    p.add_argument("--safe", action="store_true", help="Enable safe mode")
    p.add_argument("--extra", default="", help="Additional arguments")
    a = p.parse_args(tokens)

    state = "active" if a.dc else "inactive"

    return {
        "subcommand": sub,
        "domain": a.domain,
        "dc": a.dc,
        "userlist": a.userlist,
        "passwordlist": a.passwordlist,
        "safe": a.safe,
        "extra": a.extra,
        "state": state,
    }


def kerb_scan_from_ui(cmd: str, project: str):
    try:
        from core.database.neo4j.neo4j_manager import Neo4jManager

        db = Neo4jManager()

        if not db.check_project_exists(project):
            raise ValueError(f"Project with ID '{project}' does not exist.")
        db.close()

        cfg = parse_ui_input(cmd)
        cfg["project"] = project
    except SystemExit:
        return {"error": "Invalid parameters"}

    try:
        args = build_kerbrute_args(cfg)
        return scan_kerbrute("", args, project)
    except Exception as e:
        return {"error": str(e)}


def build_kerbrute_args(cfg: dict) -> List[str]:
    base = [cfg["subcommand"], "--domain", cfg["domain"]]
    if cfg.get("dc"):
        base += ["--dc", cfg["dc"]]
    if cfg.get("safe"):
        base.append("--safe")
    if cfg.get("extra"):
        base += shlex.split(cfg["extra"])

    sub = cfg["subcommand"]
    if sub == "userenum":
        if not cfg.get("userlist"):
            raise ValueError("-u/--userlist required for userenum")
        base.append(cfg["userlist"])
    elif sub == "passwordspray":
        if not cfg.get("userlist") or not cfg.get("passwordlist"):
            raise ValueError("-u and -P required for passwordspray")
        base.extend([cfg["userlist"], cfg["passwordlist"]])
    elif sub == "bruteuser":
        if not cfg.get("userlist") or not cfg.get("passwordlist"):
            raise ValueError("-u and -P required for bruteuser")
        base.extend([cfg["passwordlist"], cfg["userlist"]])
    else:
        raise ValueError(f"Unknown subcommand {sub}")

    return base
