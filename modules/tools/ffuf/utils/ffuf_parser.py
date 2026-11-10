import json


def parse_ffuf_output(output: str) -> list[dict]:
    """Parse `ffuf -json` output (one JSON record per line) into hits."""
    hits = []
    for line in output.splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue  # stray non-JSON line (warnings, banners)
        if isinstance(rec, dict) and "url" in rec:
            hits.append({"url": rec["url"], "status": rec.get("status"), "length": rec.get("length")})
    return hits
