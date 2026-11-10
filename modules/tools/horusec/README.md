# Horusec Module

Static code analysis with [Horusec](https://github.com/ZupIT/horusec).

- Endpoint: `POST /back/horusec/scan?project=<id>` with a ZIP of the source code as `file` (multipart).
- Uses the public `horuszup/horusec-cli:latest` image (pulled on first scan).
- The ZIP is extracted to `/tmp/curium/horusec/<project>` on the host, so the worker needs the `/tmp/curium` bind mount from compose.
- Findings are stored as `CodeVulnerability` nodes: `Project -[:HAS_SCAN]-> Scan -[:FOUND]-> CodeVulnerability <-[:HAS_CODE_VULN]- File`, and are included in the generated report.
