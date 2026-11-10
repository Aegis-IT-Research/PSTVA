import unittest 

from modules.tools.nikto.resolvers.nikto_resolver import SCAN_TYPES_NIKTO, NiktoResolverError, resolve_nikto_command

class TestNiktoResolver(unittest.TestCase):
    
    def test_resolver_scan_command_valid(self):
        
        target = "http://192.168.1.92"
        scan_type = "default"
        
        for scan_type in SCAN_TYPES_NIKTO.keys():
            command = resolve_nikto_command(scan_type, target)
            self.assertIn(target, command)
            self.assertIn("nikto", command)
            self.assertIn(SCAN_TYPES_NIKTO[scan_type].split()[0], command)
            
    
    def test_resolver_invalid_type(self):
        with self.assertRaises(NiktoResolverError) as cm:
            resolve_nikto_command("invalid_scan_type", "http://192.168.1.92")
        self.assertIn("invalid_scan_type", str(cm.exception)) 
        
        