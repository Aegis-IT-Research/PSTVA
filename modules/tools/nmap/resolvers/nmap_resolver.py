class NmapResolverError(Exception):
    pass


SCAN_TYPES = {
    "quick": "-T4 -F {target}",
    "service_version": "-sV -T4 {target}",
    "vulnerability": "-sV --script vulners -T4 {target}",
    "os_detection": "-O -T4 {target}",
    "top_ports": "--top-ports 1000 -T4 {target}",
}


def resolve_nmap_command(scan_type: str, target: str) -> str:

    #if scan_type not in SCAN_TYPES:
       #raise NmapResolverError(f"Invalid scan type: {scan_type}")

    try:
        template = SCAN_TYPES[scan_type]
    except KeyError:
        raise NmapResolverError(f"Invalid scan type: {scan_type}")
    data = {"target": target}
    nmap_args = template.format_map(data)
    full_command = f"nmap {nmap_args}"
    return full_command
