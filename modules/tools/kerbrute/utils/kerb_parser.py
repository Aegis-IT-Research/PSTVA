import re
from typing import Dict, List, Union


BANNER_CHARS = ("█", "═")
ANSI_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences."""

    return ANSI_RE.sub("", s)


def kerbscan_parse_output(kerbrute_text: str) -> Dict[str, List[Union[str, dict]]]:

    if not isinstance(kerbrute_text, str) or not kerbrute_text.strip():
        return {"kdcs": [], "logins": []}

    clean_text = strip_ansi(kerbrute_text)

    kdc_pattern = re.compile(r"^\s*(.+):(\d+)\s*$")
    timestamp_pattern = re.compile(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} >")
    valid_pattern = re.compile(r"\[\+\] VALID (?:LOGIN|USERNAME):\s+(.+?):(.+)")

    kdcs = []
    logins = []

    lines = clean_text.strip().split("\n")

    start_parsing = False
    for line in lines:
        # Skip banner lines
        if any(char in line for char in BANNER_CHARS):
            continue

        if timestamp_pattern.search(line):
            start_parsing = True

        if not start_parsing:
            continue

        cleaned_line = timestamp_pattern.sub("", line).strip()

        # Check for KDC
        if ":" in cleaned_line and "[+]" not in cleaned_line and cleaned_line:
            kdc_match = kdc_pattern.search(cleaned_line)
            if kdc_match:
                server = kdc_match.group(1).strip()
                port = kdc_match.group(2).strip()
                kdcs.append({"server": server, "port": port})

        # Check VALID LOGIN or USERNAME
        valid_match = valid_pattern.search(cleaned_line)
        if valid_match:
            full_username = valid_match.group(1).strip()
            password = valid_match.group(2).strip()

            # Extract username and domain
            if "@" in full_username:
                username, domain = full_username.split("@", 1)
            else:
                username = full_username
                domain = ""

            logins.append(
                {
                    "username": username,
                    "domain": domain,
                    "full_username": full_username,
                    "password": password,
                }
            )

    return {"kdcs": kdcs, "logins": logins}
