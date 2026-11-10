import unittest

from modules.tools.ffuf.resolvers.ffuf_resolver import resolve_ffuf_command
from modules.tools.ffuf.utils.ffuf_parser import parse_ffuf_output

SAMPLE = """\
{"input":{"FUZZ":"admin"},"position":1,"status":301,"length":169,"words":5,"lines":8,"url":"http://10.0.0.5/admin","host":"10.0.0.5"}
some stray warning line
{"input":{"FUZZ":"index.html"},"position":2,"status":200,"length":615,"words":55,"lines":24,"url":"http://10.0.0.5/index.html","host":"10.0.0.5"}
"""


class TestFfuf(unittest.TestCase):
    def test_resolver_dir(self):
        cmd = resolve_ffuf_command("dir", "http://10.0.0.5/")
        self.assertEqual(cmd[:2], ["-u", "http://10.0.0.5/FUZZ"])
        self.assertIn("-json", cmd)

    def test_resolver_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            resolve_ffuf_command("nope", "http://10.0.0.5")
        with self.assertRaises(ValueError):
            resolve_ffuf_command("dir", "10.0.0.5")

    def test_parser(self):
        self.assertEqual(parse_ffuf_output(SAMPLE), [
            {"url": "http://10.0.0.5/admin", "status": 301, "length": 169},
            {"url": "http://10.0.0.5/index.html", "status": 200, "length": 615},
        ])


if __name__ == "__main__":
    unittest.main()
