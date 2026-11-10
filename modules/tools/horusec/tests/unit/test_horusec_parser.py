import unittest

from pathlib import Path
from modules.tools.horusec.utils.horusec_parser import parse_horusec_output


class TestHorusecParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        real_json = (
            Path(__file__).resolve().parents[1] / "fixtures" / "horusec-result.json"
        ).read_text(encoding="utf-8")
        cls.parsed_data = parse_horusec_output(real_json)

    def test_parser_root_keys(self):
        self.assertIn("tool", self.parsed_data)
        self.assertIn("analysis", self.parsed_data)
        self.assertIn("vulnerabilities", self.parsed_data)

    def test_tool_name(self):
        self.assertEqual(self.parsed_data["tool"], "horusec")

    def test_analysis_metadata(self):
        analysis = self.parsed_data["analysis"]

        self.assertIn("id", analysis)
        self.assertIn("status", analysis)
        self.assertIn("version", analysis)
        self.assertIn("created_at", analysis)
        self.assertIn("finished_at", analysis)

    def test_vulnerabilities_not_empty(self):
        vulns = self.parsed_data["vulnerabilities"]
        self.assertIsInstance(vulns, list)
        self.assertGreater(len(vulns), 0)

    def test_first_vulnerability_schema(self):
        vuln = self.parsed_data["vulnerabilities"][0]

        expected_keys = {
            "vulnerability_id",
            "rule_id",
            "severity",
            "confidence",
            "language",
            "security_tool",
            "type",
            "file",
            "line",
            "column",
            "code",
            "details",
            "vuln_hash",
        }

        self.assertTrue(expected_keys.issubset(vuln.keys()))
