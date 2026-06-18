"""Content-hash refresh helpers for PragmaGraph snapshots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pragmagraph.adapters import index_path
from pragmagraph.adapters.git_history import DEFAULT_GIT_IDENTITY_MODE
from pragmagraph.parsers import ParserRegistry, get_default_registry
from pragmagraph.models import (
    GraphSnapshot,
    RefreshManifest,
    RefreshManifestEntry,
    RefreshPathChange,
    RefreshResult,
    SnapshotStructuralDelta,
)
from pragmagraph.portability import normalize_relative_path
from pragmagraph.security import ScopePolicy, load_gitignore, should_index_path


def build_manifest(
    root_path: str | Path,
    *,
    policy: ScopePolicy | None = None,
    parser_registry: ParserRegistry | None = None,
) -> RefreshManifest:
    """Build a deterministic content-hash manifest for indexable files."""
    root = Path(root_path).resolve()
    scope = policy or ScopePolicy()
    registry = parser_registry or get_default_registry()
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
                parser=_parser_name(path, registry=registry),
                parser_version=_parser_version(path, registry=registry),
                size_bytes=path.stat().st_size,
                file_kind=_file_kind(path),
            )
        )
    return RefreshManifest(root_path=str(root), entries=tuple(entries))


def refresh_snapshot(
    root_path: str | Path,
    *,
    namespace: str = "default",
    previous_manifest: RefreshManifest | None = None,
    previous_snapshot: GraphSnapshot | None = None,
    policy: ScopePolicy | None = None,
    created_at: str = "",
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
    parser_registry: ParserRegistry | None = None,
) -> RefreshResult:
    """Index ``root_path`` and report content changes since ``previous_manifest``."""
    root = Path(root_path).resolve()
    registry = parser_registry or get_default_registry()
    manifest = build_manifest(root_path, policy=policy, parser_registry=registry)
    snapshot = index_path(
        root,
        namespace=namespace,
        policy=policy,
        created_at=created_at,
        git_identity_mode=git_identity_mode,
        parser_registry=registry,
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
    path_changes = tuple(_path_changes(previous, current))
    return RefreshResult(
        snapshot=snapshot,
        manifest=manifest,
        changed_paths=changed,
        unchanged_paths=unchanged,
        removed_paths=removed,
        path_changes=path_changes,
        snapshot_delta=diff_snapshots(
            previous_snapshot
            or GraphSnapshot(namespace=namespace, root_path=str(root)),
            snapshot,
        ),
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


def _parser_name(path: Path, *, registry: ParserRegistry) -> str:
    selection = registry.select_parser(path)
    if selection.parser is not None:
        return selection.parser.name
    if path.suffix.lower() == ".py":
        return "python_ast"
    return "raw_file"


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
        return "javascript"
    if suffix in {".ts", ".tsx"}:
        return "typescript"
    if suffix == ".py":
        return "python"
    if suffix == ".md":
        return "markdown"
    if suffix in {".toml", ".json", ".yaml", ".yml"}:
        return "config"
    return "text"


def _parser_version(path: Path, *, registry: ParserRegistry) -> str:
    selection = registry.select_parser(path)
    if selection.parser is not None:
        return selection.parser.version
    return "pragmagraph.raw_file.v1alpha1"


def _path_changes(
    previous: dict[str, RefreshManifestEntry],
    current: dict[str, RefreshManifestEntry],
) -> list[RefreshPathChange]:
    statuses: list[RefreshPathChange] = []
    all_paths = sorted(set(previous) | set(current))
    for path in all_paths:
        before = previous.get(path)
        after = current.get(path)
        if before is None and after is not None:
            statuses.append(
                RefreshPathChange(
                    path=path,
                    status="added",
                    reasons=("new_path",),
                    current_entry=after,
                )
            )
            continue
        if before is not None and after is None:
            statuses.append(
                RefreshPathChange(
                    path=path,
                    status="removed",
                    reasons=("removed_path",),
                    previous_entry=before,
                )
            )
            continue
        assert before is not None and after is not None
        reasons: list[str] = []
        if before.content_hash != after.content_hash:
            reasons.append("content_hash_changed")
        if before.parser != after.parser:
            reasons.append("parser_changed")
        if before.parser_version != after.parser_version:
            reasons.append("parser_version_changed")
        if before.size_bytes != after.size_bytes:
            reasons.append("size_changed")
        if before.file_kind != after.file_kind:
            reasons.append("file_kind_changed")
        statuses.append(
            RefreshPathChange(
                path=path,
                status="changed" if reasons else "unchanged",
                reasons=tuple(reasons) if reasons else ("unchanged_content",),
                previous_entry=before,
                current_entry=after,
            )
        )
    return statuses


def describe_manifest_changes(
    previous_manifest: RefreshManifest,
    current_manifest: RefreshManifest,
) -> tuple[RefreshPathChange, ...]:
    """Describe deterministic path-level differences between two manifests."""
    return tuple(_path_changes(previous_manifest.by_path(), current_manifest.by_path()))


def diff_snapshots(
    before: GraphSnapshot,
    after: GraphSnapshot,
) -> SnapshotStructuralDelta:
    """Return the deterministic structural delta between two snapshots."""
    before_node_ids = {node.id for node in before.nodes}
    after_node_ids = {node.id for node in after.nodes}
    before_edge_ids = {edge.id for edge in before.edges}
    after_edge_ids = {edge.id for edge in after.edges}
    before_omitted_ids = {f"{item.reason}:{item.item_id}" for item in before.omitted}
    after_omitted_ids = {f"{item.reason}:{item.item_id}" for item in after.omitted}
    return SnapshotStructuralDelta(
        added_node_ids=tuple(sorted(after_node_ids - before_node_ids)),
        removed_node_ids=tuple(sorted(before_node_ids - after_node_ids)),
        added_edge_ids=tuple(sorted(after_edge_ids - before_edge_ids)),
        removed_edge_ids=tuple(sorted(before_edge_ids - after_edge_ids)),
        added_omitted_ids=tuple(sorted(after_omitted_ids - before_omitted_ids)),
        removed_omitted_ids=tuple(sorted(before_omitted_ids - after_omitted_ids)),
    )


__all__ = [
    "build_manifest",
    "describe_manifest_changes",
    "diff_snapshots",
    "load_manifest",
    "refresh_snapshot",
    "save_manifest",
]
