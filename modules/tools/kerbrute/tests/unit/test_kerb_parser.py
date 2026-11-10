from pathlib import Path
import unittest
from unittest import result

from modules.tools.kerbrute.utils.kerb_parser import kerbscan_parse_output


class TestKerbParser(unittest.TestCase):

    def test_kerbscan_parse_output(self):
        real_text_output = (
            Path(__file__).resolve().parents[1] / "fixtures" / "real_kerb_data.txt"
        ).read_text()
        result = kerbscan_parse_output(real_text_output)

        kdcs = result["kdcs"]
        logins = result["logins"]

        self.assertEqual(len(kdcs), 1)
        self.assertEqual(len(logins), 2)

        # KDC Testing
        self.assertTrue(any([x["server"] == "pdc01.lab.ropnop.com" for x in kdcs]))
        self.assertTrue(any([x["port"] == "88" for x in kdcs]))

        # Test Logins
        self.assertTrue(any([x["username"] == "callen" for x in logins]))
        self.assertTrue(any([x["username"] == "eshort" for x in logins]))
        self.assertTrue(any([x["password"] == "Password123" for x in logins]))
        self.assertTrue(any([x["domain"] == "lab.ropnop.com" for x in logins]))
