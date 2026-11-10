import json
import os
from pathlib import Path
import unittest
from core.infra.scripts.list_celery_jobs import list_celery_jobs_redis_service


@unittest.skipUnless(
    os.environ.get("AEGIS_RUN_SMOKE") == "1",
    "Requires running Redis (set AEGIS_RUN_SMOKE=1 to enable)",
)
class TestListCeleryJobs(unittest.TestCase):
    def test_list_celery_jobs_redis(self):
        out_file = Path(__file__).resolve().parent / "results" / f"{self._testMethodName}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        result = list_celery_jobs_redis_service()
        
        with open(out_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"saved to {out_file}")
