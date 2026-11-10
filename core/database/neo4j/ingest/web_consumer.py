from __future__ import annotations

from typing import Dict

from core.database.neo4j.neo4j_manager import Neo4jManager
from core.database.neo4j.payloads import RunMeta, WebSection


def ingest_web_section(
    web: WebSection, *, run: RunMeta, project_id: str, db: Neo4jManager
) -> Dict:
    if not db.check_project_exists(project_id):
        raise ValueError(f"Project with ID '{project_id}' does not exist.")

    website_count = 0
    with db.driver.session() as session:
        for site in web.websites:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MERGE (w:WebSite {uid: $uid})
                    SET w.scheme = $scheme,
                        w.first_seen = $first_seen,
                        w.last_seen = $last_seen,
                        w.project = $project_id
                    """,
                    uid=site.uid,
                    scheme=site.scheme,
                    first_seen=site.first_seen.isoformat()
                    if site.first_seen
                    else None,
                    last_seen=site.last_seen.isoformat()
                    if site.last_seen
                    else None,
                    project_id=project_id,
                )
            )
            website_count += 1

    return {"websites": website_count}
