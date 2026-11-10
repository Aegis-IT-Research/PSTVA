from __future__ import annotations

from typing import Dict

from core.database.neo4j.neo4j_manager import Neo4jManager
from core.database.neo4j.payloads import NetworkSection, RunMeta


def ingest_network_section(
    network: NetworkSection, *, run: RunMeta, project_id: str, db: Neo4jManager
) -> Dict:
    if not db.check_project_exists(project_id):
        raise ValueError(f"Project with ID '{project_id}' does not exist.")

    host_count = 0
    port_count = 0
    service_count = 0

    with db.driver.session() as session:
        for host in network.hosts:
            session.execute_write(
                lambda tx: tx.run(
                    """
                    MATCH (p:Project {id: $project_id})
                    MERGE (h:Host {project: $project_id, ip: $ip})
                    SET h.id = $ip,
                        h.uid = $ip,
                        h.state = $state,
                        h.hostname = $hostname,
                        h.dn = $domain,
                        h.created_at = $created_at,
                        h.last_seen = $last_seen
                    MERGE (p)-[:HAS_HOST]->(h)
                    WITH h
                    MATCH (tr:ToolRun {id: $run_id})
                    MERGE (tr)-[:SCANNED]->(h)
                    """,
                    project_id=project_id,
                    run_id=run.id,
                    ip=host.id,
                    state=host.state,
                    hostname=host.hostname or None,
                    domain=host.domain or None,
                    created_at=host.created_at.isoformat()
                    if host.created_at
                    else None,
                    last_seen=host.last_seen.isoformat() if host.last_seen else None,
                )
            )
            host_count += 1

            for port in host.ports:
                session.execute_write(
                    lambda tx: tx.run(
                        """
                        MATCH (h:Host {project: $project_id, ip: $ip})
                        MERGE (p:Port {uid: $port_uid})
                        SET p.proto = $proto,
                            p.port = $port,
                            p.state = $state,
                            p.first_seen = $first_seen,
                            p.last_seen = $last_seen,
                            p.project = $project_id
                        MERGE (h)-[:HAS_PORT]->(p)
                        """,
                        project_id=project_id,
                        ip=host.id,
                        port_uid=port.uid,
                        proto=port.proto,
                        port=port.port,
                        state=port.state,
                        first_seen=port.first_seen.isoformat()
                        if port.first_seen
                        else None,
                        last_seen=port.last_seen.isoformat()
                        if port.last_seen
                        else None,
                    )
                )
                port_count += 1

                if port.service:
                    svc = port.service
                    session.execute_write(
                        lambda tx: tx.run(
                            """
                            MATCH (p:Port {uid: $port_uid})
                            MERGE (s:Service {uid: $service_uid})
                            SET s.name = $name,
                                s.product = $product,
                                s.version = $version,
                                s.banner_hash = $banner_hash,
                                s.first_seen = $first_seen,
                                s.last_seen = $last_seen,
                                s.protocol = $protocol,
                                s.state = $state,
                                s.port = $port,
                                s.ip = $ip,
                                s.portid = $portid,
                                s.project = $project_id
                            MERGE (p)-[:RUNS]->(s)
                            WITH s
                            MATCH (h:Host {project: $project_id, ip: $ip})
                            MERGE (h)-[:Runs]->(s)
                            """,
                            project_id=project_id,
                            ip=host.id,
                            portid=port.port,
                            port_uid=port.uid,
                            service_uid=svc.uid,
                            name=svc.name,
                            product=svc.product,
                            version=svc.version,
                            banner_hash=svc.banner_hash,
                            first_seen=svc.first_seen.isoformat()
                            if svc.first_seen
                            else None,
                            last_seen=svc.last_seen.isoformat()
                            if svc.last_seen
                            else None,
                            protocol=svc.protocol or port.proto,
                            state=svc.state or port.state,
                            port=svc.port or port.port,
                        )
                    )
                    service_count += 1

                    for cpe in svc.cpe:
                        session.execute_write(
                            lambda tx: tx.run(
                                """
                                MATCH (s:Service {uid: $service_uid})
                                MERGE (c:CPE {uri: $uri})
                                SET c.project = $project_id
                                MERGE (s)-[r:HAS_CPE]->(c)
                                SET r.first_seen = $first_seen,
                                    r.last_seen = $last_seen,
                                    r.confidence = $confidence
                                """,
                                project_id=project_id,
                                service_uid=svc.uid,
                                uri=cpe.uri,
                                first_seen=cpe.first_seen.isoformat()
                                if cpe.first_seen
                                else None,
                                last_seen=cpe.last_seen.isoformat()
                                if cpe.last_seen
                                else None,
                                confidence=cpe.confidence,
                            )
                        )

    return {
        "hosts": host_count,
        "ports": port_count,
        "services": service_count,
    }
