import unittest

from pathlib import Path
from modules.tools.nmap.utils.nmap_parser import parse_nmap_output


class TestNmapParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        real_text_output = (
            Path(__file__).resolve().parents[1] / "fixtures" / "real_nmap_data.xml"
        ).read_text()
        cls.parsed_data = parse_nmap_output(real_text_output)

    def test_nmap_parser_ip(self):

        actual_result = self.parsed_data[0]["ip"]
        expected_result = "192.168.5.241"
        self.assertEqual(actual_result, expected_result)

    def test_nmap_parser_state(self):
        actual_result = self.parsed_data[0]["state"]
        expected_result = "filtered"
        self.assertEqual(actual_result, expected_result)

    def test_nmap_parser_services(self):
        actual_result = self.parsed_data[0]["services"][0]
        expected_result = {
            "portid": "1313",
            "protocol": "tcp",
            "state": "filtered",
            "name": "bmc_patroldb",
            "product": "",
            "version": "",
            "cpe": "",
        }
        self.assertEqual(actual_result, expected_result)
