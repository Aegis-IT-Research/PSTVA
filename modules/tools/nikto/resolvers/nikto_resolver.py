class NiktoResolverError(Exception):
    pass


SCAN_TYPES_NIKTO = {
    "default": "-h {target}",
    "Plugins": "-h {target} --list-plugins",
    "SSL": "-h {target} --ssl",
}

def resolve_nikto_command(scan_type: str, target: str) -> str:

    #if scan_type not in SCAN_TYPES_NIKTO:
        #raise NiktoResolverError(f"Invalid scan type: {scan_type}")

    try:
        template = SCAN_TYPES_NIKTO[scan_type]
    except KeyError:
        raise NiktoResolverError(f"Invalid scan type: {scan_type}")
    data = {"target": target}
    nikto_args = template.format_map(data)
    full_command = f"nikto {nikto_args}"
    return full_command

