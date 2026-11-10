import unittest

from modules.tools.nmap.utils.ip_ranges_utils import IPError, expand_ip_ranges


class TestExpandIpRanges(unittest.TestCase):

    def test_single_ip(self):
        result = expand_ip_ranges("192.168.1.1")
        self.assertEqual(result, ["192.168.1.1"])

    def test_simple_range(self):
        result = expand_ip_ranges("192.168.1.1-3")
        expected = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        self.assertEqual(result, expected)

    def test_mixed_ips_and_ranges(self):
        result = expand_ip_ranges("192.168.1.1,192.168.1.3-4")
        expected = ["192.168.1.1", "192.168.1.3", "192.168.1.4"]
        self.assertEqual(result, expected)

    def test_overlapping_ranges(self):
        result = expand_ip_ranges("192.168.1.1-3,192.168.1.2-4")
        expected = ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4"]
        self.assertEqual(result, expected)

    def test_big_to_small_range(self):
        result = expand_ip_ranges("192.168.1.4-1")
        expected = ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4"]
        self.assertEqual(result, expected)

    def test_empty_input(self):
        with self.assertRaises(IPError):
            expand_ip_ranges("")

    def test_domain_name(self):
        result = expand_ip_ranges("example.com")
        expected = ["example.com"]
        self.assertEqual(result, expected)

    def test_domain_and_range_mixed(self):
        result = expand_ip_ranges("example.com,128.0.0.6-7")
        expected = ["example.com", "128.0.0.6", "128.0.0.7"]
        self.assertEqual(sorted(result), sorted(expected))
