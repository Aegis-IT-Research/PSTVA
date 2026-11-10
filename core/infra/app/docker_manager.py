"""Compatibility shim.

The runtime implementation moved to `core.app.docker_runner`.
Keep this module so existing imports (modules/tools, reporting, etc.) keep working.
"""

from core.app.docker_runner import (  # noqa: F401
    DockerException,
    DockerManager,
    DockerResult,
    Timer,
)

__all__ = [
    "DockerException",
    "DockerManager",
    "DockerResult",
    "Timer",
]

