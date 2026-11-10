import os
import sys
from pathlib import Path


def _add_repo_path(p: Path) -> None:
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)


# Ensure the new scaffolded core backend package is importable in local pytest runs.
REPO_ROOT = Path(__file__).resolve().parents[2]
_add_repo_path(REPO_ROOT)

# Optional: If developers rely on `.env`, allow it to provide Neo4j creds during import.
# We do not parse .env here to avoid introducing dependencies/side effects.
