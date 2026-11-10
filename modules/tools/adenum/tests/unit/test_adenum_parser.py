from pathlib import Path
import unittest

from modules.tools.adenum.utils.ad_scan_parser import parse_adenum_output

class TestADEnumParser(unittest.TestCase):

    
    def test_adenum_parser_ip(self):
        real_text_output = (
            Path(__file__).resolve().parents[1] / "fixtures" / "real_adenum_data.txt"
        ).read_text()
        result  = parse_adenum_output(real_text_output)
        users = result["users"]
        never_expire_users = result["users_with_password_not_expire"]
        domainControllers  = result["domainControllers"]

        self.assertEqual(len(users), 2)
        self.assertTrue(any([x["username"]=="eraptis" for x in users]))

        self.assertEqual(len(never_expire_users), 4)
        self.assertTrue(any([x["username"]=="adoe" for x in never_expire_users]))

        self.assertEqual(len(domainControllers),1)
        self.assertTrue(any([x["name"]=="WIN-D9HL4AN4816" for x in domainControllers]))

