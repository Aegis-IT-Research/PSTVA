import unittest
import os
from core.infra.app.tasks import kerbrute_scan_task


@unittest.skipUnless(
    os.environ.get("AEGIS_RUN_SMOKE") == "1",
    "Requires Redis/Celery/Neo4j (set AEGIS_RUN_SMOKE=1 to enable)",
)
class TestKerbrute(unittest.TestCase):
    def test_kerbrute(self):
        async_result = kerbrute_scan_task.apply_async(
            kwargs={
                "target": "aegis.local", 
                "args": ["userenum", "-d", "aegis.local", "--dc", "192.168.1.10", "/opt/wordlists/users.txt"],
                "project": "task_id",
            }
        )

        data = {"task_id": async_result.id}
        print(data)
