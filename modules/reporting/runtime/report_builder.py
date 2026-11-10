from __future__ import annotations

import io
import os
import tarfile
from typing import Dict

from core.infra.app.docker_manager import DockerManager, DockerResult
from core.database.neo4j.neo4j_manager import Neo4jManager


IMAGE = "pentest-report-builder:latest"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# Build from modules/reporting so the Dockerfile can copy scripts/templates/findings/.
CONTEXT = os.path.join(REPO_ROOT, "modules", "reporting")
DOCKERFILE = "reportbuilder/docker/Dockerfile"


def ensure_builder_image():
    import docker

    cli = docker.from_env()
    try:
        cli.images.get(IMAGE)
    except docker.errors.ImageNotFound:
        print(f"[+] Building report builder image {IMAGE} …")
        cli.images.build(path=CONTEXT, dockerfile=DOCKERFILE, tag=IMAGE, rm=True)
        print("[+] Build complete")


def report_build_service(project: str, findings_dir: str, out_md: str, make_pdf: bool = False) -> DockerResult:
    db = Neo4jManager()
    try:
        if not db.check_project_exists(project):
            raise ValueError(f"Project with ID '{project}' does not exist.")
    finally:
        db.close()

    ensure_builder_image()

    host_reporting_root = os.path.join(REPO_ROOT, "modules", "reporting")
    container_reporting_root = "/work"

    def to_container_path(p: str) -> str:
        ap = os.path.abspath(p)
        if ap.startswith(host_reporting_root):
            rel = os.path.relpath(ap, host_reporting_root)
        else:
            rel = p
        return f"{container_reporting_root}/{rel}".replace("\\", "/")

    c_findings = to_container_path(findings_dir)
    c_out_md = to_container_path(out_md)

    volumes = {
        host_reporting_root: {"bind": container_reporting_root, "mode": "rw"}
    }

    mgr = DockerManager()

    gen_cmd = [
        "python",
        "scripts/generate_report.py",
        "--findings-dir",
        c_findings,
        "--out",
        c_out_md,
    ]
    result = mgr.run_container(
        image=IMAGE,
        command=gen_cmd,
        volumes=volumes,
        working_dir="/work",
    )

    if make_pdf:
        pdf_path = os.path.splitext(c_out_md)[0] + ".pdf"
        _ = mgr.run_container(
            image=IMAGE,
            command=[
                "python",
                "scripts/md_to_pdf_latex.py",
                "--input",
                c_out_md,
                "--output",
                pdf_path,
            ],
            volumes=volumes,
            working_dir="/work",
        )

    return result


def report_build_save(docker_result: DockerResult, project_id: str) -> Dict[str, str]:
    db = Neo4jManager()
    try:
        log_id = db.log_action(
            action="report build",
            project=project_id,
            time_started=docker_result.start_time,
            time_ended=docker_result.end_time,
            user="Default",
            command=docker_result.command,
            tool_output=docker_result.logs,
        )
        return {"log_id": str(log_id), "status": "report-generated"}
    finally:
        db.close()


def md_file_to_pdf(md_host_path: str, out_pdf_host_path: str) -> DockerResult:
    """
    Convert a markdown file on the host to PDF using the ReportBuilder container.
    Both paths must be under the host reporting root (modules/reporting) so they are visible to the container.
    Returns a DockerResult for the conversion run.
    """
    ensure_builder_image()

    import docker

    os.makedirs(os.path.dirname(out_pdf_host_path), exist_ok=True)

    client = docker.from_env()

    container = client.containers.create(
        image=IMAGE,
        command=[
            "bash",
            "-lc",
            "mkdir -p /work/uploads && "
            "python scripts/md_to_pdf_latex.py --input /work/uploads/in.md --output /work/uploads/out.pdf",
        ],
        working_dir="/work",
        detach=True,
    )

    data = open(md_host_path, "rb").read()
    fileobj = io.BytesIO()
    with tarfile.open(fileobj=fileobj, mode="w") as tar:
        ti = tarfile.TarInfo(name="uploads/in.md")
        ti.size = len(data)
        ti.mtime = int(os.path.getmtime(md_host_path)) if os.path.exists(md_host_path) else 0
        ti.mode = 0o644
        tar.addfile(ti, io.BytesIO(data))
    fileobj.seek(0)
    container.put_archive(path="/work", data=fileobj.read())

    container.start()
    exit_res = container.wait()
    logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
    status = exit_res.get("StatusCode", 1)

    if status != 0:
        try:
            container.remove(force=True)
        finally:
            pass
        raise RuntimeError(f"Report conversion failed (exit {status}). Logs:\n{logs}")

    try:
        try:
            stream, _ = container.get_archive("/work/uploads/out.pdf")
        except Exception as e:
            raise FileNotFoundError(f"Failed to retrieve PDF from container: {e}\nLogs:\n{logs}") from e

        buf = io.BytesIO(b"".join(stream))
        with tarfile.open(fileobj=buf, mode="r") as tar:
            member = tar.next()
            if member is None:
                raise FileNotFoundError("PDF not found in container archive")
            with tar.extractfile(member) as fsrc:
                with open(out_pdf_host_path, "wb") as fdst:
                    fdst.write(fsrc.read())
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass

    from datetime import datetime

    start = datetime.utcnow().isoformat()
    end = datetime.utcnow().isoformat()
    return DockerResult(
        logs=logs,
        start_time=start,
        end_time=end,
        image=IMAGE,
        command="python scripts/md_to_pdf_latex.py --input /work/uploads/in.md --output /work/uploads/out.pdf",
    )
