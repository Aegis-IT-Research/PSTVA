import os
import re
import tempfile
import logging
import unicodedata
from datetime import datetime
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from core.app.logging_utils import new_request_id, reset_request_id, set_request_id, setup_logging
from core.app.security import login_user, logout_user, validate_api_key
from core.app.tasks import (
    adenum_scan_task,
    ffuf_scan_task,
    horusec_scan_task,
    kerbrute_scan_task,
    nikto_scan_task,
    nmap_scan_task,
)
from core.database.neo4j.neo4j_manager import Neo4jManager
from core.infra.scripts.list_celery_jobs import list_celery_jobs_redis_service
from modules.reporting.runtime.report_builder import md_file_to_pdf
from modules.reporting.scripts import generate_report as _gen_report
from modules.tools.kerbrute.models.kerb_scan import KerbScanDTO
from modules.tools.ffuf.resolvers.ffuf_resolver import SCAN_TYPES_FFUF, resolve_ffuf_command
from modules.tools.horusec.models.horusec_scan import HorusecScanDTO
from modules.tools.nikto.resolvers.nikto_resolver import SCAN_TYPES_NIKTO
from modules.tools.nmap.resolvers.nmap_resolver import SCAN_TYPES

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(root_path="/back")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming = request.headers.get("x-request-id")
    rid = incoming or new_request_id()
    token = set_request_id(rid)
    try:
        response = await call_next(request)
    finally:
        reset_request_id(token)

    response.headers["X-Request-ID"] = rid
    return response


@app.exception_handler(Exception)
async def catch_all_exceptions(request: Request, exception: Exception):
    _ = request
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"error": f"{exception}"},
    )


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/jobs", dependencies=[Depends(validate_api_key)])
def list_celery_jobs():
    info = list_celery_jobs_redis_service()
    result = JSONResponse(info, status_code=200)
    return result


@app.post("/login")
def login(request: LoginRequest):
    """Authenticate a user and return an API token."""

    try:
        token = login_user(request.username, request.password)
        return {"status": "success", "token": token}
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})


@app.post("/logout", dependencies=[Depends(validate_api_key)])
def logout(username: str = Query(..., description="Username to log out")):
    """Log out a user by invalidating their API token."""

    try:
        logout_user(username)
        return {"status": "success", "message": "Logged out successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class ProjectCreateRequest(BaseModel):
    name: str


@app.post("/create_project", dependencies=[Depends(validate_api_key)])
def create_project(request: ProjectCreateRequest):
    name = request.name
    db = Neo4jManager()
    try:
        created_at = datetime.utcnow().isoformat()
        project = db.add_project(name, created_at)
        return {"status": "Project created successfully", "project": project}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.get("/projects", dependencies=[Depends(validate_api_key)])
def get_projects():
    """Fetch all projects with their names and IDs."""

    db = Neo4jManager()
    try:
        projects = db.get_all_projects()
        return projects
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.post("/report/upload_md_to_pdf", dependencies=[Depends(validate_api_key)])
async def upload_md_to_pdf(file: UploadFile = File(...)):
    """Accept a markdown upload, convert to PDF, return the PDF."""

    tmp_root = os.environ.get("TMPDIR", "/tmp")
    uploads_dir = tempfile.mkdtemp(prefix="report_upload_", dir=tmp_root)

    orig_name = os.path.basename(file.filename or "uploaded.md")
    if not orig_name.lower().endswith(".md"):
        orig_name = orig_name + ".md"

    md_path = os.path.abspath(os.path.join(uploads_dir, orig_name))
    content = await file.read()
    with open(md_path, "wb") as f:
        f.write(content)

    base = os.path.splitext(os.path.basename(md_path))[0]
    pdf_path = os.path.abspath(os.path.join(uploads_dir, base + ".pdf"))

    md_file_to_pdf(md_path, pdf_path)

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path),
    )


@app.post("/nmap/scan", dependencies=[Depends(validate_api_key)])
def nmap_scan_route(
    target: str = Query(..., description="Target IP or hostname"),
    scan_type: str = Query(..., description="Scan Type", enum=list(SCAN_TYPES.keys())),
    project: str = Query(..., description="Project ID to associate the scan results"),
):
    run_id = str(uuid4())
    async_result = nmap_scan_task.apply_async(
        kwargs={
            "target": target,
            "scan_type": scan_type,
            "project": project,
            "run_id": run_id,
        }
    )

    data = {"task_id": async_result.id, "run_id": run_id}
    return JSONResponse(status_code=202, content=data)


@app.post("/nikto/scan", dependencies=[Depends(validate_api_key)])
def nikto_scan_route(
    target: str = Query(
        ..., description="Target web server (IP/host, with http[s]:// or just host)"
    ),
    scan_type: str = Query(
        ..., description="Scan Type", enum=list(SCAN_TYPES_NIKTO.keys())
    ),
    project: str = Query(..., description="Project ID to associate the scan results"),
):
    run_id = str(uuid4())
    async_result = nikto_scan_task.apply_async(
        kwargs={
            "target": target,
            "scan_type": scan_type,
            "project": project,
            "run_id": run_id,
        }
    )

    data = {"task_id": async_result.id, "run_id": run_id}
    return JSONResponse(status_code=202, content=data)


@app.post("/adenum/scan", dependencies=[Depends(validate_api_key)])
def run_adenum_scan(
    project: str = Query(..., description="Project ID to associate the scan results"),
    domain: str = Query(..., description="Active Directory domain (e.g., corp.local)"),
    ip: str = Query(..., description="IP address of the target (e.g., 192.168.1.2)"),
    username: str = Query(..., description="Username for authentication (e.g., user)"),
    password: str = Query(
        ..., description="Password for authentication (e.g., password!123)"
    ),
):
    args = ["-d", domain, "-ip", ip, "-u", username, "-p", password]

    async_result = adenum_scan_task.apply_async(
        kwargs={
            "target": "args",
            "args": args,
            "project": project,
        }
    )

    data = {"task_id": async_result.id}
    return JSONResponse(status_code=202, content=data)


@app.post(
    "/kerbrute/scan",
    summary="Run Kerbrute from a CLI-style string",
    dependencies=[Depends(validate_api_key)],
)
def run_kerbrute_scan(request: Annotated[KerbScanDTO, Query()]):
    try:
        async_result = kerbrute_scan_task.apply_async(
            kwargs={"scan_request": request},
        )
        data = {"task_id": async_result.id}
        return JSONResponse(status_code=202, content=data)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


UPLOAD_DIR = "/data/curium/uploads"


@app.post("/horusec/scan", dependencies=[Depends(validate_api_key)])
async def horusec_scan_route(
    project: str = Query(..., description="Project ID to associate the scan results"),
    file: UploadFile = File(..., description="ZIP file containing source code"),
):
    """Run a Horusec static code analysis on an uploaded ZIP of source code."""

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    zip_path = os.path.join(UPLOAD_DIR, f"{uuid4()}.zip")
    with open(zip_path, "wb") as f:
        f.write(await file.read())

    dto = HorusecScanDTO(project_id=project, source=zip_path)
    async_result = horusec_scan_task.apply_async(kwargs={"scan_request": dto.model_dump()})
    return JSONResponse(status_code=202, content={"task_id": async_result.id})


@app.post("/ffuf/scan", dependencies=[Depends(validate_api_key)])
def ffuf_scan_route(
    target: str = Query(..., description="Base URL, e.g. http://10.0.0.5 or https://site:8443"),
    scan_type: str = Query(..., description="Scan Type", enum=list(SCAN_TYPES_FFUF.keys())),
    project: str = Query(..., description="Project ID to associate the scan results"),
):
    try:
        resolve_ffuf_command(scan_type, target)  # validate before queueing
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    async_result = ffuf_scan_task.apply_async(
        kwargs={"target": target, "scan_type": scan_type, "project": project}
    )
    return JSONResponse(status_code=202, content={"task_id": async_result.id})


@app.get("/graph", dependencies=[Depends(validate_api_key)])
def dump_graph(project: str = Query(..., description="Project ID to filter the graph data")):
    """Fetch the graph data filtered by the specified project ID."""

    db = Neo4jManager()
    try:
        if not db.check_project_exists(project):
            return JSONResponse(
                status_code=404,
                content={"error": f"Project with ID '{project}' does not exist."},
            )

        return db.dump_graph(project=project)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.get("/logs", dependencies=[Depends(validate_api_key)])
def get_logs(project_id: str = Query(..., description="Project ID to filter logs")):
    """Fetch logs for the specified project ID."""

    db = Neo4jManager()
    try:
        if not db.check_project_exists(project_id):
            return JSONResponse(
                status_code=404,
                content={"error": f"Project with ID '{project_id}' does not exist."},
            )

        cypher = """
            MATCH (l:Log {project: $project_id})
            RETURN l.id AS id, l.action AS action, l.time_started AS time_started, l.time_ended AS time_ended, l.user AS user, l.command AS command
            ORDER BY l.time_started DESC
        """
        result = db.driver.session().run(cypher, project_id=project_id)
        logs = [
            {
                "id": record["id"],
                "action": record["action"],
                "time_started": record["time_started"],
                "time_ended": record["time_ended"],
                "user": record["user"],
                "command": record["command"],
            }
            for record in result
        ]
        return {"status": "success", "logs": logs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.get("/tool_output", dependencies=[Depends(validate_api_key)])
def get_tool_output(
    project: str = Query(..., description="Project ID to filter tool outputs"),
    log_id: int = Query(..., description="Log ID to fetch tool output"),
):
    """Fetch tool output for the specified project and log ID."""

    db = Neo4jManager()
    try:
        if not db.check_project_exists(project):
            return JSONResponse(
                status_code=404,
                content={"error": f"Project with ID '{project}' does not exist."},
            )

        cypher = """
            MATCH (l:Log {project: $project, id: $log_id})
            RETURN l.tool_output AS tool_output
        """
        result = db.driver.session().run(cypher, project=project, log_id=log_id)
        record = result.single()
        if record and record["tool_output"]:
            return {"status": "success", "tool_output": record["tool_output"]}
        return {
            "status": "error",
            "message": "No tool output found for the specified log ID",
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.get("/get_findings", dependencies=[Depends(validate_api_key)])
def get_findings(
    project: str = Query(..., description="Project ID to generate findings report for"),
):
    """Generate a Markdown report from database vulnerabilities for the project."""

    db = Neo4jManager()
    try:
        if not db.check_project_exists(project):
            return JSONResponse(
                status_code=404,
                content={"error": f"Project with ID '{project}' does not exist."},
            )

        vulns = db.get_findings(project)

        with tempfile.TemporaryDirectory(prefix=f"findings_{project}_") as tmpdir:
            findings_dir = os.path.join(tmpdir, "findings")
            os.makedirs(findings_dir, exist_ok=True)
            out_path = os.path.join(tmpdir, f"report_{project}.md")

            def cvss_to_severity(cvss_val: Optional[str]) -> str:
                try:
                    v = (
                        float(cvss_val)
                        if cvss_val is not None and cvss_val != "-"
                        else None
                    )
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

            def yq(val: Optional[str]) -> str:
                if val is None:
                    return "''"
                s = str(val).replace("\n", " ").strip()
                s = s.replace("'", "''")
                return f"'{s}'"

            for idx, v in enumerate(vulns or [], start=1):
                ip = v.get("ip", "-")
                portid = v.get("portid", "-")
                svc = v.get("service_name") or "-"
                product = v.get("product") or "-"
                version = v.get("version") or "-"
                vuln_title = v.get("vuln") or "Unspecified Vulnerability"
                cvss = v.get("cvss") or "-"
                link = v.get("link") or None
                exploit = v.get("exploit") or None

                finding_id = f"{ip}:{portid}-{idx}"
                affected = f"{ip}:{portid} ({svc} {product} {version})".strip()
                severity = cvss_to_severity(cvss)
                references = []
                if link:
                    references.append(str(link))

                fm_lines = [
                    "---",
                    f"id: {yq(finding_id)}",
                    f"title: {yq(vuln_title)}",
                    f"severity: {yq(severity)}",
                    f"affected: {yq(affected)}",
                    f"status: {yq('Open')}",
                    f"remediation_summary: {yq('Patch or mitigate the affected service.')}",
                ]
                if cvss and cvss != "-":
                    fm_lines.append(f"cvss: {yq(cvss)}")
                if references:
                    fm_lines.append("references:")
                    for r in references:
                        fm_lines.append(f"  - {yq(r)}")
                fm_lines.append("---")

                body_lines = [
                    f"Vulnerability observed on `{ip}:{portid}`.",
                    "",
                    f"- Service: {svc}",
                    f"- Product: {product}",
                    f"- Version: {version}",
                ]
                if exploit:
                    body_lines.append(f"- Exploit: {exploit}")
                if link:
                    body_lines.append(f"- Reference: {link}")

                content = "\n".join(fm_lines) + "\n\n" + "\n".join(body_lines) + "\n"
                fname = os.path.join(findings_dir, f"finding_{idx}.md")
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(content)

            def pdf_safe(text) -> str:
                # pdflatex chokes on non-ASCII and control chars
                s = unicodedata.normalize("NFKC", str(text or ""))
                s = s.encode("ascii", errors="ignore").decode("ascii")
                return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)

            # Code findings (Horusec)
            for idx, v in enumerate(db.get_code_vulnerabilities(project), start=len(vulns or []) + 1):
                sev = (v.get("severity") or "").strip().capitalize()
                if sev not in ("Critical", "High", "Medium", "Low"):
                    sev = "Informational"
                fm_lines = [
                    "---",
                    f"id: {yq(f'CODE-{idx}')}",
                    f"title: {yq(v.get('rule') or 'Code Vulnerability')}",
                    f"severity: {yq(sev)}",
                    f"affected: {yq(v.get('file') or '-')}",
                    f"status: {yq('Open')}",
                    f"remediation_summary: {yq('Fix the insecure code pattern.')}",
                    "---",
                ]
                body_lines = [
                    f"- Tool: {pdf_safe(v.get('tool'))}",
                    f"- Confidence: {pdf_safe(v.get('confidence'))}",
                    f"- File: {pdf_safe(v.get('file'))}",
                    f"- Line: {pdf_safe(v.get('line'))}",
                    "",
                    "Details:",
                    pdf_safe(v.get("details")),
                ]
                if v.get("code"):
                    body_lines += ["", "```", pdf_safe(v.get("code")), "```"]
                content = "\n".join(fm_lines) + "\n\n" + "\n".join(body_lines) + "\n"
                with open(os.path.join(findings_dir, f"finding_{idx}.md"), "w", encoding="utf-8") as f:
                    f.write(content)

            old_cwd = os.getcwd()
            reporting_dir = os.environ.get("AEGIS_REPORTING_DIR")
            if not reporting_dir:
                reporting_dir = os.path.abspath(os.path.join(old_cwd, "modules", "reporting"))
            try:
                os.chdir(reporting_dir)
                _gen_report.main(
                    [
                        "--findings-dir",
                        findings_dir,
                        "--out",
                        out_path,
                    ]
                )
            finally:
                os.chdir(old_cwd)

            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    md = f.read()
            else:
                md = f"# Findings for project {project}\n\n_No findings available._\n"

            headers = {
                "Content-Disposition": f"attachment; filename=report_{project}.md"
            }
            return Response(content=md, media_type="text/markdown", headers=headers)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.delete("/delete_project", dependencies=[Depends(validate_api_key)])
def delete_project(project_id: str):
    db = Neo4jManager()
    try:
        if not db.check_project_exists(project_id):
            return JSONResponse(
                status_code=404,
                content={"error": f"Project with ID '{project_id}' does not exist."},
            )

        db.delete_project(project_id)
        return {"status": "Project deleted successfully"}
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()


@app.delete("/delete_database", dependencies=[Depends(validate_api_key)])
def delete_database():
    """Delete all nodes and relationships in the Neo4j database."""

    db = Neo4jManager()
    try:
        cypher = """
            MATCH (n)
            DETACH DELETE n
        """
        db.driver.session().run(cypher)
        return {"status": "success", "message": "Database deleted successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        db.close()
