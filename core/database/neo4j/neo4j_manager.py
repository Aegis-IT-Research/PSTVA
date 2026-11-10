import json
import os
import uuid 
from neo4j import GraphDatabase

USER = os.environ["NEO4J_USER"]
PASS = os.environ["NEO4J_PASS"]


class Neo4jManager:
    def __init__(self, uri="bolt://neo4j:7687"):
        self.driver = GraphDatabase.driver(uri, auth=(USER, PASS))


    def close(self):
        self.driver.close()


    def clear_database(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


    def add_host(self, ip, project, state, hostname=None, dn=None, os=None):
        """
        Add or update a Host node. If the host is a domain controller, additional
        properties (hostname, dn, os) are set. Handles merging of parameters.
        """
        # Check if the host already exists for the given IP and project
        check_host_cypher = """
            MATCH (h:Host {ip: $ip, project: $project})
            RETURN h.hostname AS old_hostname, h.dn AS old_dn, h.os AS old_os
        """

        # Create or update the host
        create_or_update_host_cypher = """
            MERGE (h:Host {ip: $ip, project: $project})
            SET h.hostname = $hostname,
                h.state = $state,
                h.dn = $dn,
                h.os = $os
                
        """

        # Prepare parameters
        params = {
            "ip": ip,
            "project": project,
            "state": state,
            "hostname": hostname,
            "dn": dn,
            "os": os,
        }

        with self.driver.session() as session:
            # Check if the host exists
            result = session.run(check_host_cypher, ip=ip, project=project)
            record = result.single()

            if record:
                # Host exists, handle merging of parameters
                old_hostname = record["old_hostname"]
                old_dn = record["old_dn"]
                old_os = record["old_os"]

                # Merge hostname
                if old_hostname is None:
                    params["hostname"] = hostname
                elif hostname is None:
                    params["hostname"] = old_hostname
                elif old_hostname != hostname:
                    params["hostname"] = f"{old_hostname}, {hostname}"

                # Merge dn
                if old_dn is None:
                    params["dn"] = dn
                elif dn is None:
                    params["dn"] = old_dn
                elif old_dn != dn:
                    params["dn"] = f"{old_dn}, {dn}"

                # Merge os
                if old_os is None:
                    params["os"] = os
                elif os is None:
                    params["os"] = old_os
                elif old_os != os:
                    params["os"] = f"{old_os}, {os}"

            # Create or update the host with merged parameters
            session.run(create_or_update_host_cypher, params)


    def get_all_data(self, project: str):
        cypher = """
            
            MATCH (h:Host {project: $project})
            OPTIONAL MATCH (h)-[:Runs]->(s:Service)
            OPTIONAL MATCH (s)-[:HAS_VULN]->(v:Vulnerability)

            // collect vulns per service to avoid cartesian duplication
            WITH h, s,
                collect(DISTINCT v)                    AS vulns

            // pack each service into a map and collect per host
            WITH h,
                collect(
                    CASE WHEN s IS NULL
                        THEN NULL                     // no services at all
                        ELSE s { .*,                 // all service props …
                            vulnerabilities: [ x IN vulns WHERE x IS NOT NULL | x {.*} ]
                        }
                    END
                )                                      AS services

            // final projection: one row per host
            RETURN h { .*, services: [x IN services WHERE x IS NOT NULL] } AS host
        """

        with self.driver.session() as session:
            result = session.run(cypher, project=project)
            # each record already contains a fully formed Python dict
            return [record["host"] for record in result]

    def get_findings(self, project: str):
        """
        Return a list of vulnerabilities for a given project with related host/service info.
        Each item: {ip, portid, service_name, product, version, vuln, cvss, link, exploit}
        """
        cypher = """
            MATCH (h:Host {project: $project})-[:Runs]->(s:Service)
            OPTIONAL MATCH (s)-[:HAS_VULN]->(v:Vulnerability)
            WITH h, s, v
            WHERE v IS NOT NULL
            RETURN h.ip AS ip,
                   s.portid AS portid,
                   s.name AS service_name,
                   s.product AS product,
                   s.version AS version,
                   v.vuln AS vuln,
                   v.cvss AS cvss,
                   v.link AS link,
                   v.exploit AS exploit
            ORDER BY ip, toInteger(portid)
        """
        with self.driver.session() as session:
            result = session.run(cypher, project=project)
            return [
                {
                    "ip": r["ip"],
                    "portid": r["portid"],
                    "service_name": r.get("service_name"),
                    "product": r.get("product"),
                    "version": r.get("version"),
                    "vuln": r["vuln"],
                    "cvss": r.get("cvss"),
                    "link": r.get("link"),
                    "exploit": r.get("exploit"),
                }
                for r in result
            ]


    def add_net_service(
            self,
            ip: str,
            portid: int,
            protocol: str = None,
            state: str = None,
            name: str = None,
            product: str = None,
            version: str = None,
            cpe: str = None,
            project: str = None,  # Added project as a parameter
    ):
        """
        Create or update a Service node keyed on (ip, portid, project) and attach it to
        the matching Host. Existing services are overwritten with the new data.
        """
        # Normalize portid to integer to avoid duplicates due to type mismatch
        if portid is not None and not isinstance(portid, int):
            try:
                portid = int(portid)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid portid value: {portid}")
        cypher = """
            // make sure we have the Host first
            MATCH (h:Host {ip: $ip, project: $project})

            // (ip, portid, project) is the identity for a Service
            MERGE (h)-[:Runs]->(s:Service {ip: $ip, portid: $portid, project: $project})

            // overwrite / fill in the rest of the attributes
            SET s.protocol = $protocol,
                s.state    = $state,
                s.name     = $name,
                s.product  = $product,
                s.version  = $version,
                s.cpe      = $cpe
        """

        params = dict(
            ip=ip,
            portid=portid,
            protocol=protocol,
            state=state,
            name=name,
            product=product,
            version=version,
            cpe=cpe,
            project=project,  # Pass the project parameter
        )

        with self.driver.session() as session:
            summary = session.execute_write(lambda tx, p: tx.run(cypher, **p).consume(), params)
        return summary.counters


    def add_vulnerability(
            self,
            ip: str,
            portid: int,
            vuln: str,
            cvss: str = None,
            link: str = None,
            exploit: str = None,
            project: str = None,  # Added project as a parameter
    ):
        """
        Add or update a Vulnerability node and link it to the correct Service node.
        """
        # Normalize portid to integer to avoid duplicates due to type mismatch
        if portid is not None and not isinstance(portid, int):
            try:
                portid = int(portid)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid portid value: {portid}")
        cypher = """
            MATCH (s:Service {ip: $ip, portid: $portid, project: $project})
            MERGE (v:Vulnerability {vuln: $vuln, ip: $ip, portid: $portid, project: $project})
            SET v.cvss = $cvss,
                v.link = $link,
                v.exploit = $exploit
            MERGE (s)-[:HAS_VULN]->(v)
        """

        params = dict(
            ip=ip,
            portid=portid,
            vuln=vuln,
            cvss=cvss,
            link=link,
            exploit=exploit,
            project=project,  # Ensure the project is included in the query
        )

        with self.driver.session() as session:
            summary = session.execute_write(
                lambda tx, p: tx.run(cypher, **p).consume(), params
            )

        return summary.counters


    def create_scan(self, project_id: str, scan: dict) -> None:
        cypher = """
            MATCH (p:Project {id: $project_id})
            CREATE (s:Scan {
                id: $id,
                tool: $tool,
                started_at: $started_at,
                finished_at: $finished_at,
                status: $status,
                project: $project_id
            })
            MERGE (p)-[:HAS_SCAN]->(s)
        """
        params = {
            "project_id": project_id,
            "id": scan.get("id"),
            "tool": scan.get("tool"),
            "started_at": scan.get("started_at"),
            "finished_at": scan.get("finished_at"),
            "status": scan.get("status"),
        }
        with self.driver.session() as session:
            session.execute_write(lambda tx, p: tx.run(cypher, **p).consume(), params)


    def add_code_vulnerability(
            self,
            project: str,
            scan_id: str,
            tool: str,
            severity: str = None,
            confidence: str = None,
            rule: str = None,
            file: str = None,
            line: int = None,
            column: int = None,
            code: str = None,
            details: str = None,
            hash: str = None,
    ):
        cypher = """
            MATCH (s:Scan {id: $scan_id})
            MERGE (f:File {project: $project, path: $file})
            MERGE (v:CodeVulnerability {project: $project, hash: $hash})
            SET v.tool = $tool,
                v.severity = $severity,
                v.confidence = $confidence,
                v.rule = $rule,
                v.file = $file,
                v.line = $line,
                v.column = $column,
                v.code = $code,
                v.details = $details,
                v.timestamp = datetime()
            MERGE (s)-[:FOUND]->(v)
            MERGE (f)-[:HAS_CODE_VULN]->(v)
        """
        params = {
            "project": project,
            "scan_id": scan_id,
            "hash": hash or str(uuid.uuid4()),
            "tool": tool,
            "severity": severity,
            "confidence": confidence,
            "rule": rule,
            "file": file,
            "line": line,
            "column": column,
            "code": code,
            "details": details,
        }
        with self.driver.session() as session:
            session.execute_write(lambda tx, p: tx.run(cypher, **p).consume(), params)


    def get_code_vulnerabilities(self, project: str):
        cypher = """
            MATCH (p:Project {id: $project})-[:HAS_SCAN]->(s:Scan)-[:FOUND]->(v:CodeVulnerability)
            OPTIONAL MATCH (f:File)-[:HAS_CODE_VULN]->(v)
            RETURN s.id AS scan_id, v.tool AS tool, v.severity AS severity,
                   v.confidence AS confidence, v.rule AS rule, f.path AS file,
                   v.line AS line, v.column AS column, v.code AS code,
                   v.details AS details, v.hash AS hash
            ORDER BY s.started_at DESC, v.severity
        """
        with self.driver.session() as session:
            return [r.data() for r in session.run(cypher, project=project)]


    def add_web_path(self, ip: str, portid: int, scheme: str, url: str,
                     status: int, length: int, project: str):
        """Attach a discovered web path (FFuF hit) to its Service.
        Host/Service are created if missing but never overwritten, so Nmap data survives."""
        cypher = """
            MERGE (h:Host {ip: $ip, project: $project})
              ON CREATE SET h.state = 'up'
            MERGE (h)-[:Runs]->(s:Service {ip: $ip, portid: $portid, project: $project})
              ON CREATE SET s.protocol = 'tcp', s.state = 'open', s.name = $scheme
            MERGE (w:WebPath {url: $url, project: $project})
            SET w.status = $status, w.length = $length
            MERGE (s)-[:HAS_PATH]->(w)
        """
        params = dict(ip=ip, portid=int(portid), scheme=scheme, url=url,
                      status=status, length=length, project=project)
        with self.driver.session() as session:
            session.execute_write(lambda tx, p: tx.run(cypher, **p).consume(), params)


    def dump_graph(self, project: str):
        with self.driver.session() as s:
            # Fetch nodes
            node_records = s.run(
                """
                MATCH (n)
                WHERE n.project = $project
                RETURN elementId(n) AS id, labels(n)[0] AS label, properties(n) AS props
                """,
                project=project
            )
            # props first: Scan/Log nodes have their own `id` property, which
            # must not overwrite the graph id that links point at
            nodes = [
                {
                    **r["props"],
                    "id": r["id"],
                    "group": r["label"],
                }
                for r in node_records
            ]

            # Fetch links
            link_records = s.run(
                """
                MATCH (n)-[r]->(m)
                WHERE n.project = $project AND m.project = $project
                RETURN elementId(r) AS id, elementId(n) AS source, elementId(m) AS target, type(r) AS type, properties(r) AS props
                """,
                project=project
            )
            links = [
                {
                    "id": r["id"],
                    "source": r["source"],
                    "target": r["target"],
                    "type": r["type"],
                    **r["props"],
                }
                for r in link_records
            ]

            # Filter out invalid links
            valid_node_ids = {node["id"] for node in nodes}
            links = [link for link in links if link["source"] in valid_node_ids and link["target"] in valid_node_ids]

            return {"nodes": nodes, "links": links}


    def get_all_projects(self):
        """
        Retrieve all projects with their IDs and creation timestamps.
        """
        cypher = """
            MATCH (p:Project)
            RETURN p.id AS id, p.name AS name, p.created_at AS created_at
        """

        with self.driver.session() as session:
            result = session.run(cypher)
            return [{"id": record["id"], "name": record["name"], "created_at": record["created_at"]} for record in result]


    def add_project(self, name: str, created_at: str):
        """
        Add a new project with a unique ID. If a project with the same name exists, return an error.
        """
        # Check if the project already exists
        check_project_cypher = """
            MATCH (p:Project {name: $name})
            RETURN p
        """

        # Create the project if it doesn't exist
        create_project_cypher = """
            CREATE (p:Project {id: $id, name: $name, created_at: $created_at})
        """

        with self.driver.session() as session:
            # Check if the project exists
            result = session.run(check_project_cypher, name=name)
            if result.single():
                raise ValueError(f"Project with name '{name}' already exists.")

            # Generate a unique ID for the project
            project_id = str(uuid.uuid4())

            # Create the project
            session.run(create_project_cypher, id=project_id, name=name, created_at=created_at)
            return {"id": project_id, "name": name, "created_at": created_at}


    def delete_project(self, project_id: str):
        """
        Delete a project and all its associated data using the project ID.
        """
        cypher = """
            // Delete all nodes associated with the project
            MATCH (n)
            WHERE n.project = $project_id
            DETACH DELETE n

            // Delete the Project node itself
            WITH COUNT(n) AS deletedNodes
            MATCH (p:Project {id: $project_id})
            DETACH DELETE p
        """

        with self.driver.session() as session:
            session.run(cypher, project_id=project_id)


    def log_action(self, action: str, project: str, time_started, time_ended, user: str = None, command: str = None, tool_output: str = None):
        """
        Log an action performed on a project with an incremental ID.
        """
        # Query to calculate the next ID
        get_next_id_cypher = """
            MATCH (l:Log {project: $project})
            RETURN COALESCE(MAX(l.id), 0) + 1 AS next_id
        """

        # Query to create the log entry
        create_log_cypher = """
            CREATE (l:Log {
                id: $id,
                action: $action,
                project: $project,
                timestamp: datetime(),
                time_started: $time_started,
                time_ended: $time_ended,
                user: $user,
                command: $command,
                tool_output: $tool_output
            })
        """

        with self.driver.session() as session:
            # Get the next ID for the log
            result = session.run(get_next_id_cypher, project=project)
            next_id = result.single()["next_id"]

            # Create the log entry with the incremental ID
            session.run(
                create_log_cypher,
                id=next_id,
                action=action,
                project=project,
                time_started=time_started,
                time_ended=time_ended,
                user=user,
                command=command,
                tool_output=tool_output
            )
            return next_id

    def get_logs(self, project: str):
        """
        Retrieve all logs for a specific project.
        """
        cypher = """
            MATCH (l:Log {project: $project})
            RETURN l.id AS id, l.action AS action, l.time_started AS time_started, l.time_ended AS time_ended, l.user AS user, l.command AS command
            ORDER BY l.timestamp DESC
        """

        with self.driver.session() as session:
            result = session.run(cypher, project=project)
            return [record.data() for record in result]


    def get_tool_output_by_id(self, log_id: str):
        """
        Retrieve the tool output for a specific log entry by its ID.
        """
        cypher = """
            MATCH (l:Log)
            WHERE l.id = $log_id
            RETURN l.tool_output AS tool_output
        """

        with self.driver.session() as session:
            result = session.run(cypher, log_id=log_id)
            record = result.single()
            return record["tool_output"] if record else None


    def add_user(self, username: str, dn: str | None, roles: list[str], host_ip: str, project: str):
        """
        Add a User node and link it to a Host node.
        """
        cypher = """
            MERGE (u:User {username: $username, project: $project})
            SET u.dn = $dn,
                u.roles = $roles
            WITH u
            MATCH (h:Host {ip: $host_ip, project: $project})
            MERGE (h)-[:HAS_USER]->(u)
        """
        params = {
            "username": username,
            "dn": dn,
            "roles": roles,
            "host_ip": host_ip,
            "project": project,
        }
        with self.driver.session() as session:
            session.run(cypher, params)


    def add_domain_controller(self, name: str, dn: str | None, os: str):
        with self.driver.session() as s:
            s.run(
                """
                MERGE (d:DomainController {name:$name, project:'ad_enum'})
                SET   d.dn=$dn, d.os=$os
                """,
            name=name, dn=dn, os=os
        )

    # TODO: ASK: is this an actual check???
    def check_project_exists(self, project_id: str) -> bool:
        """
        Check if a project with the given ID exists in the database.
        """
        cypher = """
            MATCH (p:Project {id: $project_id})
            RETURN p
        """
        with self.driver.session() as session:
            result = session.run(cypher, project_id=project_id)
            return result.single() is not None
