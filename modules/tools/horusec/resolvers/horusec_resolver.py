from modules.tools.horusec.models.horusec_scan import HorusecScanDTO

def resolve_horusec_command(payload: HorusecScanDTO) -> list[str]:
    return [
        "horusec",
        "start",
        "--output-format", "json",
        "--json-output-file", "/workspace/horusec-result.json",
        "-p", "/workspace",
        "--disable-docker",
    ]
