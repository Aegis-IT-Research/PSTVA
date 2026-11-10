import os
import sys
from pathlib import Path


def _add_repo_path(p: Path) -> None:
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


# Ensure running pytest from any subfolder still imports repo packages.
REPO_ROOT = Path(__file__).resolve().parent
_add_repo_path(REPO_ROOT)


# Some modules import `Neo4jManager` at import-time and expect these env vars.
# Setting defaults here avoids test collection failures in local environments.
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASS", "neo4j")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("APP_USER", "default")
os.environ.setdefault("APP_PASSWORD", "default")
