from dataclasses import asdict
import logging

from celery import Celery
from celery import chain

from core.app.docker_runner import DockerResult
from core.app.logging_utils import setup_logging

from core.database.neo4j.ingest.legacy_ingesters import (
    persist_legacy_nikto_payload,
    persist_legacy_nmap_payload,
)

from modules.tools.nmap.scripts.nmap_scan import nmap_build_combined_payload, nmap_scan_service
from modules.tools.nikto.scripts.nikto_scan import (
    nikto_build_combined_payload,
    nikto_scan_service,
)
from modules.tools.adenum.scripts.ad_scan import adenum_scan_service, adenum_scan_save
from modules.tools.kerbrute.scripts.kerb_scan import (
    kerbrute_scan_service,
    kerbrute_scan_save,
)
from modules.tools.horusec.scripts.horusec_scan import horusec_scan_service, horusec_scan_save
from modules.tools.horusec.models.horusec_scan import HorusecScanDTO
from modules.tools.ffuf.scripts.ffuf_scan import ffuf_scan_service, ffuf_scan_save
from modules.reporting.runtime.report_builder import (
    report_build_service,
    report_build_save,
)

from modules.tools.nmap.utils.ip_ranges_utils import expand_ip_ranges


setup_logging()
logger = logging.getLogger(__name__)


celery_app = Celery(
    broker=f"redis://redis:6379/0",
    backend=f"redis://redis:6379/1",
)

# Keep Celery from reconfiguring logging so our stdout format is consistent.
celery_app.conf.update(
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)

# Celery's default app discovery looks for `app` or `celery`.
# Keep `celery_app` for backward compatibility and expose `app` as an alias.
app = celery_app




@celery_app.task(name="app.tasks.nmap_scan_service_task", bind=True)
def nmap_scan_service_task(self, target: str, scan_type: str, project: str, run_id: str):
    logger.info("task_start nmap_scan_service_task id=%s target=%s scan_type=%s project=%s run_id=%s", self.request.id, target, scan_type, project, run_id)
    docker_result = nmap_scan_service(target, scan_type, project, run_id=run_id)
    dict_result = asdict(docker_result)
    dict_result["scan_type"] = scan_type
    dict_result["run_id"] = run_id
    logger.info("task_done nmap_scan_service_task id=%s", self.request.id)
    return dict_result


@celery_app.task(name="app.tasks.nmap_scan_save_task", bind=True)
def nmap_scan_save_task(self, dict_result: dict, project_id: str, run_id: str):
    logger.info("task_start nmap_scan_save_task id=%s project=%s run_id=%s", self.request.id, project_id, run_id)
    scan_type = dict_result.get("scan_type") or "unknown"
    run_id = dict_result.get("run_id") or run_id
    docker_result = DockerResult(
        logs=dict_result["logs"],
        start_time=dict_result["start_time"],
        end_time=dict_result["end_time"],
        image=dict_result["image"],
        command=dict_result["command"],
    )

    try:
        payload = nmap_build_combined_payload(
            docker_result,
            project_id=project_id,
            scan_type=scan_type,
            run_id=run_id,
        )
    except Exception as e:
        dict_result = {
            "status": "error",
            "reason": "nmap parse error",
            "error": f"Error building combined payload: {e}",
            "project_id": project_id,
            "run_id": run_id,
        }
        logger.info("task_done nmap_scan_save_task id=%s", self.request.id)
        return dict_result

    dict_result = persist_legacy_nmap_payload(payload)
    logger.info("task_done nmap_scan_save_task id=%s", self.request.id)
    return dict_result


@celery_app.task(name="app.tasks.nmap_scan_task", bind=True)
def nmap_scan_task(self, target: str, scan_type: str, project: str, run_id: str):
    logger.info("task_start nmap_scan_task id=%s target=%s scan_type=%s project=%s run_id=%s", self.request.id, target, scan_type, project, run_id)
    targets = expand_ip_ranges(target)
    multi = len(targets) > 1
    for x in targets:
        per_target_run_id = f"{run_id}:{x}" if multi else run_id
        chain_ = nmap_scan_service_task.s(x, scan_type, project, per_target_run_id) | nmap_scan_save_task.s(
            project_id=project, run_id=per_target_run_id
        )
        chain_.apply_async()
    logger.info("task_done nmap_scan_task id=%s", self.request.id)
    return "OK"


@celery_app.task(name="app.tasks.nikto_scan_service_task", bind=True)
def nikto_scan_service_task(self, target: str, scan_type: str, project: str, run_id: str):
    logger.info("task_start nikto_scan_service_task id=%s target=%s scan_type=%s project=%s run_id=%s", self.request.id, target, scan_type, project, run_id)
    dr = nikto_scan_service(target, scan_type, project)
    dict_result = asdict(dr)
    dict_result["scan_type"] = scan_type
    dict_result["run_id"] = run_id
    logger.info("task_done nikto_scan_service_task id=%s", self.request.id)
    return dict_result


@celery_app.task(name="app.tasks.nikto_scan_save_task", bind=True)
def nikto_scan_save_task(self, dict_result: dict, project_id: str, run_id: str):
    logger.info("task_start nikto_scan_save_task id=%s project=%s run_id=%s", self.request.id, project_id, run_id)
    scan_type = dict_result.get("scan_type") or "default"
    run_id = dict_result.get("run_id") or run_id
    dr = DockerResult(
        logs=dict_result["logs"],
        start_time=dict_result["start_time"],
        end_time=dict_result["end_time"],
        image=dict_result["image"],
        command=dict_result["command"],
    )
    try:
        payload = nikto_build_combined_payload(
            dr,
            project_id=project_id,
            scan_type=scan_type,
            run_id=run_id,
        )
    except Exception as e:
        dict_result = {
            "status": "error",
            "reason": "nikto parse error",
            "error": f"Error building combined payload: {e}",
            "project_id": project_id,
            "run_id": run_id,
        }
        logger.info("task_done nikto_scan_save_task id=%s", self.request.id)
        return dict_result

    out = persist_legacy_nikto_payload(payload)
    logger.info("task_done nikto_scan_save_task id=%s", self.request.id)
    return out


@celery_app.task(name="app.tasks.nikto_scan_task", bind=True)
def nikto_scan_task(self, target: str, scan_type: str, project: str, run_id: str):
    logger.info("task_start nikto_scan_task id=%s target=%s scan_type=%s project=%s run_id=%s", self.request.id, target, scan_type, project, run_id)
    targets = expand_ip_ranges(target)
    multi = len(targets) > 1
    for x in targets:
        per_target_run_id = f"{run_id}:{x}" if multi else run_id
        chain_ = nikto_scan_service_task.s(x, scan_type, project, per_target_run_id) | nikto_scan_save_task.s(
            project_id=project, run_id=per_target_run_id
        )
        chain_.apply_async()
    logger.info("task_done nikto_scan_task id=%s", self.request.id)
    return "OK"


@celery_app.task(name="app.tasks.adenum_scan_service_task", bind=True)
def adenum_scan_service_task(self, target: str, args: list, project: str):
    logger.info("task_start adenum_scan_service_task id=%s project=%s", self.request.id, project)
    dr = adenum_scan_service(target, args, project)
    logger.info("task_done adenum_scan_service_task id=%s", self.request.id)
    return asdict(dr)


@celery_app.task(name="app.tasks.adenum_scan_save_task", bind=True)
def adenum_scan_save_task(self, dict_result: dict, project_id: str):
    logger.info("task_start adenum_scan_save_task id=%s project=%s", self.request.id, project_id)
    dr = DockerResult(**dict_result)
    out = adenum_scan_save(dr, project_id)
    logger.info("task_done adenum_scan_save_task id=%s", self.request.id)
    return out


@celery_app.task(name="app.tasks.adenum_scan_task", bind=True)
def adenum_scan_task(self, target: str, args: list, project: str):
    logger.info("task_start adenum_scan_task id=%s project=%s", self.request.id, project)
    chain(
        adenum_scan_service_task.s(target, args, project),
        adenum_scan_save_task.s(project_id=project),
    ).apply_async()
    logger.info("task_done adenum_scan_task id=%s", self.request.id)
    return {"status": "queued", "project": project}


@celery_app.task(name="app.tasks.kerbrute_scan_service_task", bind=True)
def kerbrute_scan_service_task(self, target: str, args: list, project: str):
    logger.info("task_start kerbrute_scan_service_task id=%s project=%s", self.request.id, project)
    dr = kerbrute_scan_service(target, args, project)
    logger.info("task_done kerbrute_scan_service_task id=%s", self.request.id)
    return asdict(dr)


@celery_app.task(name="app.tasks.kerbrute_scan_save_task", bind=True)
def kerbrute_scan_save_task(self, dict_result: dict, project_id: str):
    logger.info("task_start kerbrute_scan_save_task id=%s project=%s", self.request.id, project_id)
    dr = DockerResult(**dict_result)
    out = kerbrute_scan_save(dr, project_id)
    logger.info("task_done kerbrute_scan_save_task id=%s", self.request.id)
    return out


@celery_app.task(name="app.tasks.kerbrute_scan_task", bind=True)
def kerbrute_scan_task(self, target: str, args: list, project: str):
    logger.info("task_start kerbrute_scan_task id=%s project=%s", self.request.id, project)
    chain(
        kerbrute_scan_service_task.s(target, args, project),
        kerbrute_scan_save_task.s(project_id=project),
    ).apply_async()
    logger.info("task_done kerbrute_scan_task id=%s", self.request.id)
    return {"status": "queued", "project": project}


@celery_app.task(name="app.tasks.horusec_scan_service_task", bind=True)
def horusec_scan_service_task(self, scan_request: dict):
    logger.info("task_start horusec_scan_service_task id=%s", self.request.id)
    dr = horusec_scan_service(HorusecScanDTO(**scan_request), scan_request["project_id"])
    return asdict(dr)


@celery_app.task(name="app.tasks.horusec_scan_save_task", bind=True)
def horusec_scan_save_task(self, dict_result: dict, project_id: str):
    logger.info("task_start horusec_scan_save_task id=%s project=%s", self.request.id, project_id)
    return horusec_scan_save(DockerResult(**dict_result), project_id)


@celery_app.task(name="app.tasks.horusec_scan_task", bind=True)
def horusec_scan_task(self, scan_request: dict):
    project_id = scan_request["project_id"]
    chain(
        horusec_scan_service_task.s(scan_request),
        horusec_scan_save_task.s(project_id=project_id),
    ).apply_async()
    return {"status": "queued", "project": project_id}


@celery_app.task(name="app.tasks.ffuf_scan_service_task", bind=True)
def ffuf_scan_service_task(self, target: str, scan_type: str, project: str):
    logger.info("task_start ffuf_scan_service_task id=%s target=%s scan_type=%s", self.request.id, target, scan_type)
    return asdict(ffuf_scan_service(target, scan_type, project))


@celery_app.task(name="app.tasks.ffuf_scan_save_task", bind=True)
def ffuf_scan_save_task(self, dict_result: dict, project_id: str, target: str):
    logger.info("task_start ffuf_scan_save_task id=%s project=%s", self.request.id, project_id)
    return ffuf_scan_save(DockerResult(**dict_result), project_id, target)


@celery_app.task(name="app.tasks.ffuf_scan_task", bind=True)
def ffuf_scan_task(self, target: str, scan_type: str, project: str):
    chain(
        ffuf_scan_service_task.s(target, scan_type, project),
        ffuf_scan_save_task.s(project_id=project, target=target),
    ).apply_async()
    return {"status": "queued", "project": project}


@celery_app.task(name="app.tasks.report_build_service_task", bind=True)
def report_build_service_task(
    self,
    project: str, findings_dir: str, out_md: str, make_pdf: bool = False
):
    logger.info("task_start report_build_service_task id=%s project=%s", self.request.id, project)
    dr = report_build_service(project, findings_dir, out_md, make_pdf)
    logger.info("task_done report_build_service_task id=%s", self.request.id)
    return asdict(dr)


@celery_app.task(name="app.tasks.report_build_save_task", bind=True)
def report_build_save_task(self, dict_result: dict, project_id: str):
    logger.info("task_start report_build_save_task id=%s project=%s", self.request.id, project_id)
    dr = DockerResult(**dict_result)
    out = report_build_save(dr, project_id)
    logger.info("task_done report_build_save_task id=%s", self.request.id)
    return out


@celery_app.task(name="app.tasks.report_build_task", bind=True)
def report_build_task(
    self,
    project: str, findings_dir: str, out_md: str, make_pdf: bool = False
):
    logger.info("task_start report_build_task id=%s project=%s", self.request.id, project)
    chain(
        report_build_service_task.s(project, findings_dir, out_md, make_pdf),
        report_build_save_task.s(project_id=project),
    ).apply_async()
    logger.info("task_done report_build_task id=%s", self.request.id)
    return {"status": "queued", "project": project}
