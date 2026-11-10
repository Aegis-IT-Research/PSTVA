from urllib.parse import urlparse

WORDLIST = "/wordlists/directory-list.txt"

# Extra ffuf args per scan type. -ac auto-calibrates away catch-all responses.
SCAN_TYPES_FFUF = {
    "dir": ["-w", WORDLIST, "-ac"],
    "extensions": ["-w", WORDLIST, "-ac", "-e", ".php,.html,.txt,.bak"],
}


def resolve_ffuf_command(scan_type: str, target: str) -> list[str]:
    if scan_type not in SCAN_TYPES_FFUF:
        raise ValueError(f"Invalid FFuF scan type: {scan_type}")
    if urlparse(target).scheme not in ("http", "https"):
        raise ValueError("FFuF target must be a URL starting with http:// or https://")
    # -json -s: one JSON record per hit on stdout, nothing else
    return ["-u", target.rstrip("/") + "/FUZZ", *SCAN_TYPES_FFUF[scan_type], "-json", "-s"]
