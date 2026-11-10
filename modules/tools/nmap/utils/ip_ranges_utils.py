import re
from typing import List


class IPError(Exception):
    pass


def expand_ip_ranges(input_str: str) -> List[str]:
    result = []
    parts = input_str.split(",")

    for part in parts:
        match = re.match(r"^(\d+\.\d+\.\d+\.)(\d+)-(\d+)$", part)
        if match:
            base = match.group(1)
            start = int(match.group(2))
            end = int(match.group(3))
            if start > end:
                start, end = end, start
            result.extend([f"{base}{i}" for i in range(start, end + 1)])
        else:
            result.append(part.strip())

    result = sorted(set(result))
    if result == [""]:
        raise IPError
    return result
