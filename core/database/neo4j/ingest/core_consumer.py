from __future__ import annotations

from typing import Dict

from core.database.neo4j.neo4j_manager import Neo4jManager
from core.database.neo4j.payloads import CoreSection, RunMeta


def ingest_core_section(
    core: CoreSection, *, run: RunMeta, project_id: str, db: Neo4jManager
) -> Dict:
    if not db.check_project_exists(project_id):
        raise ValueError(f"Project with ID '{project_id}' does not exist.")

    with db.driver.session() as session:
        session.execute_write(
            lambda tx: tx.run(
                """
                MATCH (p:Project {id: $project_id})
                MERGE (tr:ToolRun {id: $run_id})
                SET tr.tool = $tool,
                    tr.version = $version,
                    tr.args = $args,
                    tr.command = $command,
                    tr.started_at = $started_at,
                    tr.finished_at = $finished_at,
                    tr.exit_code = $exit_code,
                    tr.project = $project_id
                MERGE (p)-[:HAS_RUN]->(tr)
                """,
                project_id=project_id,
                run_id=run.id,
                tool=run.tool,
                version=run.version,
                args=run.args,
                command=run.command,
                started_at=run.started_at.isoformat() if run.started_at else None,
                finished_at=run.finished_at.isoformat() if run.finished_at else None,
                exit_code=run.exit_code,
            )
        )

        for a in core.artifacts:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MERGE (a:Artifact {id: $id})
                    SET a.kind = $kind,
                        a.created_at = $created_at,
                        a.sha256 = $sha256,
                        a.raw_text = $raw_text,
                        a.size_bytes = $size_bytes,
                        a.truncated = $truncated,
                        a.project = $project_id
                    WITH a
                    MATCH (tr:ToolRun {id: $run_id})
                    MERGE (tr)-[:PRODUCED]->(a)
                    """,
                    id=a.id,
                    kind=a.kind,
                    created_at=a.created_at.isoformat(),
                    sha256=a.sha256,
                    raw_text=a.raw_text,
                    size_bytes=a.size_bytes,
                    truncated=a.truncated,
                    project_id=project_id,
                    run_id=run.id,
                )
            )

        for f in core.findings:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MERGE (f:Finding {uid: $uid})
                    SET f.title = $title,
                        f.severity = $severity,
                        f.category = $category,
                        f.cve = $cve,
                        f.cvss = $cvss,
                        f.status = $status,
                        f.first_seen = $first_seen,
                        f.last_seen = $last_seen,
                        f.project = $project_id
                    WITH f
                    MATCH (p:Project {id: $project_id})
                    MERGE (p)-[:HAS_FINDINGS]->(f)
                    WITH f
                    MATCH (tr:ToolRun {id: $run_id})
                    MERGE (tr)-[:FOUND]->(f)
                    """,
                    uid=f.uid,
                    title=f.title,
                    severity=f.severity,
                    category=f.category,
                    cve=f.cve,
                    cvss=f.cvss,
                    status=f.status,
                    first_seen=f.first_seen.isoformat(),
                    last_seen=f.last_seen.isoformat(),
                    project_id=project_id,
                    run_id=run.id,
                )
            )

            if f.target:
                session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (f:Finding {uid: $finding_uid})
                        WITH f
                        MATCH (t {uid: $target_uid, project: $project_id})
                        MERGE (t)-[:HAS_FINDING]->(f)
                        """,
                        finding_uid=f.uid,
                        target_uid=f.target.uid,
                        project_id=project_id,
                    )
                )

        for e in core.evidence:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MERGE (e:Evidence {id: $id})
                    SET e.kind = $kind,
                        e.summary = $summary,
                        e.snippet = $snippet,
                        e.line_start = $line_start,
                        e.line_end = $line_end,
                        e.json_pointer = $json_pointer,
                        e.created_at = $created_at,
                        e.project = $project_id
                    WITH e
                    MATCH (tr:ToolRun {id: $run_id})
                    MERGE (e)-[:FROM_RUN]->(tr)
                    """,
                    id=e.id,
                    kind=e.kind,
                    summary=e.summary,
                    snippet=e.snippet,
                    line_start=e.line_start,
                    line_end=e.line_end,
                    json_pointer=e.json_pointer,
                    created_at=e.created_at.isoformat(),
                    project_id=project_id,
                    run_id=run.id,
                )
            )

            if e.finding_uid:
                session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (f:Finding {uid: $finding_uid})
                        MATCH (e:Evidence {id: $evidence_id})
                        MERGE (f)-[:SUPPORTED_BY]->(e)
                        """,
                        finding_uid=e.finding_uid,
                        evidence_id=e.id,
                    )
                )

            if e.artifact_id:
                session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (e:Evidence {id: $evidence_id})
                        MATCH (a:Artifact {id: $artifact_id})
                        MERGE (e)-[:FROM_ARTIFACT]->(a)
                        """,
                        evidence_id=e.id,
                        artifact_id=e.artifact_id,
                    )
                )

    return {
        "artifacts": len(core.artifacts),
        "findings": len(core.findings),
        "evidence": len(core.evidence),
    }
