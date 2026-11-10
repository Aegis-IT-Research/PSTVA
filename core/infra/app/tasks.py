"""Compatibility shim.

The runtime implementation moved to `core.app.tasks`.
Keep this module so existing imports and older compose/entrypoints keep working.
"""

from core.app.tasks import *  # noqa: F403

