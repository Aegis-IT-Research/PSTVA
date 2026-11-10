import unittest


from modules.tools.nmap.resolvers.nmap_resolver import (
    SCAN_TYPES,
    NmapResolverError,
    resolve_nmap_command,
)


class TestNmapResolver(unittest.TestCase):

    def test_resolve_scan_command_valid(self):
        target = "192.168.1.92"
        scan_type = "vulnerability"
        for scan_type in SCAN_TYPES.keys():
            command = resolve_nmap_command(scan_type, target)
            self.assertIn(target, command)
            self.assertIn("nmap", command)
            self.assertIn(SCAN_TYPES[scan_type].split()[0], command)

    def test_resolver_scan_invalid_type(self):
        with self.assertRaises(NmapResolverError) as cm:
            resolve_nmap_command("invalid_scan_type", "192.168.1.92")
        self.assertIn("invalid_scan_type", str(cm.exception))
