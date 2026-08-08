"""Shared parser helpers."""

from __future__ import annotations

from pathlib import Path


def module_name(rel: str) -> str:
    """Return the dotted module name represented by a repository-relative path."""
    path = Path(rel)
    parts = list(path.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or path.stem


def script_language(rel: str) -> str:
    """Return the script language family represented by a repository-relative path."""
    suffix = Path(rel).suffix.lower()
    return "typescript" if suffix in {".ts", ".tsx"} else "javascript"


__all__ = ["module_name", "script_language"]
