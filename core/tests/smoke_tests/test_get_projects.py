import unittest
import os
from core.database.neo4j.neo4j_manager import Neo4jManager


@unittest.skipUnless(
    os.environ.get("AEGIS_RUN_SMOKE") == "1",
    "Requires running Neo4j (set AEGIS_RUN_SMOKE=1 to enable)",
)
class TestGetProjects(unittest.TestCase):
    def test_get_projects(self):
        db = Neo4jManager()
        projects = db.get_all_projects()
        print(projects)
