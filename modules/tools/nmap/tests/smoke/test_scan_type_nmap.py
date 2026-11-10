import unittest
import os
from uuid import uuid4

from core.infra.app.tasks import nmap_scan_task
from modules.tools.nmap.resolvers.nmap_resolver import resolve_nmap_command


@unittest.skipUnless(
    os.environ.get("AEGIS_RUN_SMOKE") == "1",
    "Requires Redis/Celery/Neo4j (set AEGIS_RUN_SMOKE=1 to enable)",
)
class TestNmap(unittest.TestCase):
    def test_nmap(self):
        scan_type = "quick"
        target = "192.168.1.92"
        args = resolve_nmap_command(scan_type, target)
        self.assertIn("nmap", args)
        async_result = nmap_scan_task.apply_async(
            kwargs={
                "target": target,
                "scan_type": scan_type,
                "project": "b080bfe8-d179-4a17-bf3e-b2e735d85a6f",
                "run_id": str(uuid4()),
            }
        )

        data = {"task_id": async_result.id}
        print(data)
