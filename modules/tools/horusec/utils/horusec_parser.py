import json
from typing import Any, Dict, List


class HorusecParseError(Exception):
    pass

def parse_horusec_output(json_string: str) -> Dict[str, Any]:
    """
    Parse Horusec JSON output and return structured data.
    """

    if not isinstance(json_string, str) or not json_string.strip():
        raise HorusecParseError("Empty or invalid Horusec JSON input.")

    try:
        data = json.loads(json_string)
    except json.JSONDecodeError as e:
        preview = json_string[:200].replace("\n", "\\n")
        raise HorusecParseError(
            f"Failed to parse Horusec JSON: {e}. Preview: {preview}"
        ) from e

    analysis_id = data.get("id")
    status = data.get("status")
    version = data.get("version")
    created_at = data.get("createdAt")
    finished_at = data.get("finishedAt")

    analysis_vulns = data.get("analysisVulnerabilities") or []

    vulnerabilities: List[Dict[str, Any]] = []

    for item in analysis_vulns:
        v = (item or {}).get("vulnerabilities") or {}

        vulnerabilities.append(
            {
                "vulnerability_id": v.get("vulnerabilityID"),
                "rule_id": v.get("rule_id"),
                "severity": v.get("severity"),
                "confidence": v.get("confidence"),
                "language": v.get("language"),
                "security_tool": v.get("securityTool"),
                "type": v.get("type"),
                "file": v.get("file"),
                "line": int(v["line"]) if str(v.get("line", "")).isdigit() else None,
                "column": int(v["column"]) if str(v.get("column", "")).isdigit() else None,
                "code": v.get("code"),
                "details": v.get("details"),
                "vuln_hash": v.get("vulnHash"),
            }
        )

    return {
        "tool": "horusec",
        "analysis": {
            "id": analysis_id,
            "status": status,
            "version": version,
            "created_at": created_at,
            "finished_at": finished_at,
        },
        "vulnerabilities": vulnerabilities,
    }
