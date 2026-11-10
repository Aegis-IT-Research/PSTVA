"""Legacy ingesters for the pre-v2 Neo4j schema."""

from .legacy_nmap_consumer import (  # noqa: F401
    ingest_legacy_nmap_payload,
    log_legacy_nmap_failure,
    persist_legacy_nmap_payload,
)
from .legacy_nikto_consumer import (  # noqa: F401
    ingest_legacy_nikto_payload,
    log_legacy_nikto_failure,
    persist_legacy_nikto_payload,
)
