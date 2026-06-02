"""Content-hash refresh helpers for PragmaGraph snapshots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.models import RefreshManifest, RefreshManifestEntry, RefreshResult
from pragmagraph.portability import normalize_relative_path
from pragmagraph.security import ScopePolicy, load_gitignore, should_index_path


def build_manifest(
    root_path: str | Path,
    *,
    policy: ScopePolicy | None = None,
) -> RefreshManifest:
    """Build a deterministic content-hash manifest for indexable files."""
    root = Path(root_path).resolve()
    scope = policy or ScopePolicy()
    gitignore_patterns = load_gitignore(root) if scope.respect_gitignore else ()
    entries: list[RefreshManifestEntry] = []
    for path in sorted(root.rglob("*")):
        allowed, _diagnostic = should_index_path(
            path,
            root,
            scope,
            gitignore_patterns=gitignore_patterns,
        )
        if not allowed or not path.is_file():
            continue
        rel = normalize_relative_path(path.relative_to(root))
        entries.append(
            RefreshManifestEntry(
                path=rel,
                content_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
                parser=_parser_name(path),
                parser_version="pragmagraph.parser.v1alpha1",
            )
        )
    return RefreshManifest(entries=tuple(entries))


def refresh_snapshot(
    root_path: str | Path,
    *,
    namespace: str = "default",
    previous_manifest: RefreshManifest | None = None,
    policy: ScopePolicy | None = None,
    created_at: str = "",
) -> RefreshResult:
    """Index ``root_path`` and report content changes since ``previous_manifest``."""
    manifest = build_manifest(root_path, policy=policy)
    snapshot = index_path(
        root_path,
        namespace=namespace,
        policy=policy,
        created_at=created_at,
    )
    previous = (previous_manifest or RefreshManifest()).by_path()
    current = manifest.by_path()
    changed = tuple(
        path
        for path, entry in sorted(current.items())
        if previous.get(path) is None
        or previous[path].content_hash != entry.content_hash
        or previous[path].parser_version != entry.parser_version
    )
    unchanged = tuple(
        path
        for path, entry in sorted(current.items())
        if previous.get(path) is not None
        and previous[path].content_hash == entry.content_hash
        and previous[path].parser_version == entry.parser_version
    )
    removed = tuple(path for path in sorted(previous) if path not in current)
    return RefreshResult(
        snapshot=snapshot,
        manifest=manifest,
        changed_paths=changed,
        unchanged_paths=unchanged,
        removed_paths=removed,
    )


def load_manifest(path: str | Path) -> RefreshManifest:
    """Load a refresh manifest from JSON."""
    return RefreshManifest.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_manifest(manifest: RefreshManifest, path: str | Path) -> None:
    """Save a refresh manifest as deterministic JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parser_name(path: Path) -> str:
    return "python_ast" if path.suffix.lower() == ".py" else "raw_file"


__all__ = [
    "build_manifest",
    "load_manifest",
    "refresh_snapshot",
    "save_manifest",
]
