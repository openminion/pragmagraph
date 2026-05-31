"""Portable identifiers and path helpers for PragmaGraph snapshots."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


def normalize_relative_path(path: str | Path) -> str:
    """Return a stable slash-separated relative path."""
    text = str(path).replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    return "/".join(part for part in text.split("/") if part and part != ".")


def pragma_uri(namespace: str, kind: str, identifier: str) -> str:
    """Build a deterministic ``pragma://`` URI."""
    normalized_namespace = quote(str(namespace or "default").strip(), safe="")
    normalized_kind = quote(str(kind or "node").strip(), safe="")
    normalized_identifier = quote(normalize_relative_path(identifier), safe="/:@#.-_")
    return f"pragma://{normalized_namespace}/{normalized_kind}/{normalized_identifier}"


def node_id(namespace: str, kind: str, key: str) -> str:
    """Build a stable node id."""
    return pragma_uri(namespace, kind, key)


def edge_id(namespace: str, source_id: str, kind: str, target_id: str) -> str:
    """Build a stable edge id."""
    key = f"{source_id}|{kind}|{target_id}"
    return pragma_uri(namespace, "edge", key)


__all__ = [
    "edge_id",
    "node_id",
    "normalize_relative_path",
    "pragma_uri",
]
