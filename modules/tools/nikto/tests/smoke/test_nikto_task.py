import unittest
import os
from uuid import uuid4

from core.infra.app.tasks import nikto_scan_task


@unittest.skipUnless(
    os.environ.get("AEGIS_RUN_SMOKE") == "1",
    "Requires Redis/Celery/Neo4j (set AEGIS_RUN_SMOKE=1 to enable)",
)
class TestNikto(unittest.TestCase):
    def test_nikto(self):
        async_result = nikto_scan_task.apply_async(
            kwargs={
                "target": "http://192.168.1.105",
                "scan_type": "default",
                "project": "bac62150-e553-48a9-86c5-4f5c4d69045e",
                "run_id": str(uuid4()),
            }
        )

        data = {"task_id": async_result.id}
        print(data)
