"""Neo4j-specific ingestion consumers."""

from .combined_consumer import (  # noqa: F401
    ingest_combined_payload,
    persist_combined_payload,
)

from .core_consumer import ingest_core_section  # noqa: F401
from .network_consumer import ingest_network_section  # noqa: F401
from .web_consumer import ingest_web_section  # noqa: F401
