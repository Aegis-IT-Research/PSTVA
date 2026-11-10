import unittest
import os
from core.infra.app.tasks import adenum_scan_task


@unittest.skipUnless(
    os.environ.get("AEGIS_RUN_SMOKE") == "1",
    "Requires Redis/Celery/Neo4j (set AEGIS_RUN_SMOKE=1 to enable)",
)
class TestAdenum(unittest.TestCase):
    def test_adenum(self):
        async_result = adenum_scan_task.apply_async(
            kwargs={
                "target": "aegis.local",
                "args": ["-d", "aegis.local", "-ip", "192.168.1.10", "-u", "testuser", "-p", "Password123!"],
                "project": "task_id",
            }
        )

        data = {"task_id": async_result.id}
        print(data)
