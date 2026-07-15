"""Package-internal incremental extraction cache contracts."""

from pragmagraph.incremental.cache import (
    build_cache_fingerprint,
    load_extraction_cache,
    save_extraction_cache,
)
from pragmagraph.incremental.models import (
    CACHE_SCHEMA_VERSION,
    CacheFingerprint,
    ExtractionCacheBundle,
    FileIndexFragment,
)

__all__ = [
    "CACHE_SCHEMA_VERSION",
    "CacheFingerprint",
    "ExtractionCacheBundle",
    "FileIndexFragment",
    "build_cache_fingerprint",
    "load_extraction_cache",
    "save_extraction_cache",
]
