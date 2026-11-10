
from modules.tools.kerbrute.models.kerb_scan import KerbScanDTO, KerbScanType


class KerbruteResolverError(Exception):
    pass


def resolve_kerb_command(dto: KerbScanDTO) -> str:

    template = dto.scan_type.value

    if dto.scan_type.value == "passwordspray" and not dto.password:
        raise KerbruteResolverError("Password is required for passwordspray scan type")

    if dto.scan_type.value == "bruteuser" and not dto.username:
        raise KerbruteResolverError("Username is required for bruteuser scan type")

    if dto.scan_type.value == "bruteuser" and not dto.password:
        raise KerbruteResolverError("Password is required for bruteuser scan type")

    data = {
        "domain": dto.domain,
        "ip": dto.ip,
        "wordlist": dto.wordlist,
        "username": dto.username,
        "password": dto.password,
    }

    try:
        kerbrute_args = template.format_map(data)
        full_command = f"kerbrute {kerbrute_args}"
        return full_command
    except KeyError as e:
        raise KerbruteResolverError(f"Missing required parameter: {e}")
    except Exception as e:
        raise KerbruteResolverError(f"Error formatting command: {e}")
