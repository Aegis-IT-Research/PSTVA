import unittest

from modules.tools.horusec.resolvers.horusec_resolver import resolve_horusec_command
from modules.tools.horusec.models.horusec_scan import HorusecScanDTO


class TestHorusecResolver(unittest.TestCase):

    def test_resolver_generates_valid_horusec_command(self):
        dto = HorusecScanDTO(
            project_id="test_project",
            source="/tmp/fake.zip",
        )

        command = resolve_horusec_command(dto)

        self.assertIn("start", command)
        self.assertIn("--output-format", command)
        self.assertIn("json", command)
        self.assertIn("--json-output-file", command)
        self.assertIn("/workspace/horusec-result.json", command)
        self.assertIn("-p", command)
        self.assertIn("/workspace", command)
        self.assertIn("--disable-docker", command)
