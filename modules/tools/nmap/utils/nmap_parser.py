import xml.etree.ElementTree as ET


class NmapXMLParseError(Exception):
    pass


def parse_nmap_output(xml_output):
    """Parse Nmap XML output and return a list of host dicts."""
    if not xml_output or not isinstance(xml_output, (str, bytes)):
        raise NmapXMLParseError("Empty or invalid Nmap output; expected XML string.")
    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError as e:
        preview = (
            xml_output[:200]
            if isinstance(xml_output, str)
            else xml_output.decode("utf-8", errors="replace")[:200]
        )
        raise NmapXMLParseError(f"Failed to parse Nmap XML: {e}. Preview: {preview}") from e

    parsed_data = []

    for host in root.findall("host"):
        ip = ""
        state = ""
        hostname = ""
        domain = ""
        services = []
        vulnerabilities = []

        status = host.find("status")
        if status is not None:
            state = status.get("state")

        for addr in host.findall("address"):
            if addr.get("addrtype") == "ipv4":
                ip = addr.get("addr")

        ports = host.find("ports")
        if ports is not None:
            for port in ports.findall("port"):
                service = port.find("service")
                if service is not None:
                    product = service.get("product", "")
                    extrainfo = service.get("extrainfo", "")
                    if "local" in product or "local" in extrainfo:
                        domain = product if "local" in product else extrainfo

                portid = port.get("portid")
                protocol = port.get("protocol")
                state = (
                    port.find("state").get("state")
                    if port.find("state") is not None
                    else "unknown"
                )
                name = service.get("name", "") if service is not None else ""
                product = service.get("product", "") if service is not None else ""
                version = service.get("version", "") if service is not None else ""
                cpe = (
                    service.find("cpe").text
                    if service is not None and service.find("cpe") is not None
                    else ""
                )
                services.append(
                    {
                        "portid": portid,
                        "protocol": protocol,
                        "state": state,
                        "name": name,
                        "product": product,
                        "version": version,
                        "cpe": cpe,
                    }
                )

                scripts = port.findall("script[@id='vulners']")
                if scripts is not None:
                    for script in scripts:
                        output = script.get("output")
                        if not output:
                            continue
                        for line in output.splitlines():
                            line = line.strip()
                            if not line or line.startswith("cpe:"):
                                continue
                            parts = line.split("\t")
                            if len(parts) < 3:
                                continue
                            vulnerability = parts[0]
                            cvss = parts[1]
                            link = parts[2]
                            exploit = parts[3] if len(parts) > 3 else ""
                            vulnerabilities.append(
                                {
                                    "portid": portid,
                                    "vulnerability": vulnerability,
                                    "cvss": cvss,
                                    "link": link,
                                    "exploit": exploit,
                                }
                            )

        parsed_data.append(
            {
                "ip": ip,
                "state": state,
                "hostname": hostname,
                "domain": domain,
                "services": services,
                "vulnerabilities": vulnerabilities,
            }
        )

    return parsed_data
