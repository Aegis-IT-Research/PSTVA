import re


BANNER_CHARS = ("█", "═")
ANSI_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
IPV4_RE = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
DOMAIN_RE = re.compile(r"\[\*\]\s*Domain(?:\s*name)?:\s*([^\s]+)", re.IGNORECASE)


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def clean_lines(text: str):
    """
    Yield useful lines (strip banners, ANSI, blank lines).
    Keep original content except trimmed at ends.
    """

    for raw in strip_ansi(text).splitlines():
        ln = raw.strip()
        if not ln:
            continue
        # skip banner lines that start with banner characters (first char test)
        if ln[0] in BANNER_CHARS:
            continue
        yield ln


def parse_adenum_output(text: str) -> dict:
    """
    Robust parser for ADenum CLI output.
    Returns multiple commonly-used keys so frontends with different expectations
    can find data easily.
    """

    admins = []
    never_exp = []
    controllers = []
    dns = set()
    domain_name = None
    ip = None
    section = None

    lines = list(clean_lines(text))

    # Header pass: extract IP and domain
    for ln in lines:
        if ip is None:
            m = IPV4_RE.search(ln)
            if m:
                ip = m.group(0)
        if domain_name is None:
            m = DOMAIN_RE.search(ln)
            if m:
                domain_name = m.group(1).strip()
        # collect any CN=... occurrences anywhere on a line
        for cnm in re.findall(r"\bCN=[^,;\n]+(?:,[^,;\n]+)*", ln, re.IGNORECASE):
            # normalize whitespace
            dns.add(cnm.strip())

    # Main parse: detect sections and extract items
    for ln in lines:
        lower_ln = ln.lower()

        # update section markers (be permissive)
        if "users who are domain admin" in lower_ln or "users who are domain admins" in lower_ln:
            section = "admins"
            continue
        if "domain controllers" in lower_ln and "computer:" not in lower_ln and "cn=" not in lower_ln:
            section = "controllers"
            continue
        if "users with password not expire" in lower_ln or "users with password never expire" in lower_ln:
            section = "never_exp"
            continue
        # sometimes sections are introduced with [-] Domain Controllers and items follow

        # parse admin users: lines containing 'username:' and a CN=
        if section == "admins" and "username" in lower_ln:
            # allow arbitrary prefix like "[*] " so search anywhere
            m = re.search(r"Username:\s*(\S+)(?:\s+|,)\s*CN=(.+)", ln, re.IGNORECASE)
            if m:
                username = m.group(1).strip()
                dn = "CN=" + m.group(2).strip()
                admins.append({"username": username, "dn": dn})
                dns.add(dn)
            else:
                # try looser parse: username token followed later by CN=
                m2 = re.search(r"(\S+)\s+CN=(.+)", ln)
                if m2:
                    admins.append({"username": m2.group(1).strip(), "dn": "CN=" + m2.group(2).strip()})
                    dns.add("CN=" + m2.group(2).strip())
            continue

        # parse domain controllers
        if section == "controllers":
            # look for lines containing 'Computer:' and a CN= or name
            if "computer:" in ln.lower():
                after = ln.split("Computer:", 1)[1].strip()
                # common format: NAME$ CN=...,OU=Domain Controllers,...
                # split by whitespace before CN= if present
                parts = re.split(r"\s+(?=CN=)", after, maxsplit=1)
                if len(parts) == 2:
                    name = parts[0].strip().rstrip("$")
                    dn = parts[1].strip()
                else:
                    # fallback: split the first token as name, the rest as dn
                    parts2 = after.split(None, 1)
                    name = parts2[0].strip().rstrip("$")
                    dn = parts2[1].strip() if len(parts2) > 1 else ""
                controller = {"name": name}
                if dn:
                    controller["dn"] = dn
                    dns.add(dn)
                controllers.append(controller)
                continue
            # capture OS lines that might appear just after the controller line
            os_match = re.search(r"OS:\s*(.+)", ln, re.IGNORECASE)
            if os_match and controllers:
                controllers[-1]["os"] = os_match.group(1).strip()
            # also capture lines like "[V] Windows Server 2022 Standard 10.0 (20348)"
            ver_match = re.search(r"\bWindows\b.*\d{4}.*\(|\bWindows\b.*\d+\.\d+", ln)
            if ver_match and controllers and "os" not in controllers[-1]:
                controllers[-1]["os"] = ln.strip()
            continue

        # parse users whose password never expires
        if section == "never_exp" and "username" in lower_ln:
            m = re.search(r"Username:\s*(\S+)(?:\s+|,)\s*CN=(.+)", ln, re.IGNORECASE)
            if m:
                username = m.group(1).strip()
                dn = "CN=" + m.group(2).strip()
                never_exp.append({"username": username, "dn": dn})
                dns.add(dn)
            else:
                # fallback
                m2 = re.search(r"(\S+)\s+CN=(.+)", ln)
                if m2:
                    never_exp.append({"username": m2.group(1).strip(), "dn": "CN=" + m2.group(2).strip()})
                    dns.add("CN=" + m2.group(2).strip())
            continue

    # return lots of aliases for frontend flexibility
    result = {
        # canonical keys used by this parser
        "ip": ip,
        "domain": domain_name,
        "users": admins,
        "users_with_password_not_expire": never_exp,
        "domainControllers": controllers,
        "distinguishedNames": sorted(dns),
    }

    # alias keys (common variations frontends may look for)
    result["domainName"] = result["domain"]
    result["domain_name"] = result["domain"]
    result["admins"] = result["users"]
    result["domain_admins"] = result["users"]
    result["domain_controllers"] = result["domainControllers"]
    result["dnList"] = result["distinguishedNames"]

    return result
