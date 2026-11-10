from pathlib import Path
import unittest

from modules.tools.nikto.scripts.nikto_scan import parse_nikto_output

class TestNiktoParser(unittest.TestCase):

    
    def test_nikto_parser_ip(self):
        real_text_output = (
            Path(__file__).resolve().parents[1] / "fixtures" / "real_nikto_data.txt"
        ).read_text()
        host, ip, port, banner, vulnerabilities = parse_nikto_output(real_text_output)
        self.assertEqual(host,"192.168.1.105")
        self.assertEqual(ip,"192.168.1.105")
        self.assertEqual(port,"80")
        self.assertEqual(banner, "Apache/2.2.14 (Unix) DAV/2 mod_ssl/2.2.14 OpenSSL/0.9.8l PHP/5.3.1 mod_apreq2-20090110/2.7.1 mod_perl/2.0.4 Perl/v5.10.1")
        self.assertListEqual(
            sorted(vulnerabilities[0]),
            sorted(["/","","Cookie PHPSESSID created without the httponly flag"]
            )
        )



