import unittest

from modules.tools.kerbrute.resolvers.kerb_resolver import resolve_kerb_command
from modules.tools.kerbrute.models.kerb_scan import KerbScanDTO, KerbScanType


class TestKerbResolver(unittest.TestCase):

    def test_resolver_scan_command_valid(self):
        dto = KerbScanDTO(
            project="some_project",
            scan_type=KerbScanType.bruteuser,
            domain="aegis.local",
            ip="192.168.1.10",
            wordlist="/opt/wordlists/users.txt",
            username="eraptis",
            password="something",
        )

        command = resolve_kerb_command(dto)

        expected = f"kerbrute bruteuser -d aegis.local --dc 192.168.1.10 /opt/wordlists/users.txt eraptis"
        self.assertEqual(command, expected)
