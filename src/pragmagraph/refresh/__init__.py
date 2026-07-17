"""Content-hash refresh helpers for PragmaGraph snapshots."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pragmagraph.adapters import index_path
from pragmagraph.adapters.git_history import DEFAULT_GIT_IDENTITY_MODE
from pragmagraph.parsers import ParserRegistry, get_default_registry
from pragmagraph.models import (
    GraphSnapshot,
    IdentityTransition,
    RefreshManifest,
    RefreshManifestEntry,
    RefreshPathChange,
    RefreshResult,
    RefreshWorkStats,
    SnapshotStructuralDelta,
)
from pragmagraph.incremental.engine import build_incremental_snapshot
from pragmagraph.incremental.models import ExtractionCacheBundle
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
    return _build_refresh_result(
        snapshot=snapshot,
        manifest=manifest,
        namespace=namespace,
        previous_manifest=previous_manifest,
        previous_snapshot=previous_snapshot,
        work=RefreshWorkStats(
            strategy="full",
            paths_walked=sum(1 for _ in root.rglob("*")),
            source_bytes_hashed=sum(entry.size_bytes for entry in manifest.entries),
            parsed_path_count=len(manifest.entries),
            resolution_overlay_rebuilt=True,
            git_overlay_rebuilt=True,
        ),
    )


def refresh_snapshot_incremental(
    root_path: str | Path,
    *,
    namespace: str = "default",
    previous_manifest: RefreshManifest | None = None,
    previous_snapshot: GraphSnapshot | None = None,
    previous_cache: ExtractionCacheBundle | None = None,
    policy: ScopePolicy | None = None,
    created_at: str = "",
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
    parser_registry: ParserRegistry | None = None,
) -> tuple[RefreshResult, ExtractionCacheBundle]:
    """Refresh with an explicit rebuildable extraction cache."""
    root = Path(root_path).resolve()
    scope = policy or ScopePolicy()
    registry = parser_registry or get_default_registry()
    manifest = build_manifest(root, policy=scope, parser_registry=registry)
    build = build_incremental_snapshot(
        root,
        namespace=namespace,
        manifest=manifest,
        previous_snapshot=previous_snapshot,
        previous_cache=previous_cache,
        policy=scope,
        parser_registry=registry,
        created_at=created_at,
        git_identity_mode=git_identity_mode,
    )
    result = _build_refresh_result(
        snapshot=build.snapshot,
        manifest=manifest,
        namespace=namespace,
        previous_manifest=previous_manifest,
        previous_snapshot=previous_snapshot,
        work=build.work,
        identity_transitions=build.identity_transitions,
    )
    return result, build.cache


def _build_refresh_result(
    *,
    snapshot: GraphSnapshot,
    manifest: RefreshManifest,
    namespace: str,
    previous_manifest: RefreshManifest | None,
    previous_snapshot: GraphSnapshot | None,
    work: RefreshWorkStats,
    identity_transitions: tuple[IdentityTransition, ...] = (),
) -> RefreshResult:
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
            or GraphSnapshot(namespace=namespace, root_path=snapshot.root_path),
            snapshot,
        ),
        identity_transitions=identity_transitions,
        work=work,
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


@dataclass(frozen=True)
class CiDeltaReport:
    """Deterministic CI-facing snapshot delta without semantic judgment."""

    structural: SnapshotStructuralDelta
    changed_node_ids: tuple[str, ...] = ()
    changed_edge_ids: tuple[str, ...] = ()
    changed_snapshot_fields: tuple[str, ...] = ()
    fail_on_changes: bool = False

    @property
    def has_changes(self) -> bool:
        structural_changes = any(self.structural.to_dict().values())
        return bool(
            self.changed_node_ids
            or self.changed_edge_ids
            or self.changed_snapshot_fields
            or structural_changes
        )

    @property
    def exit_code(self) -> int:
        return 1 if self.fail_on_changes and self.has_changes else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": "pragmagraph.ci_delta.v1alpha1",
            "has_changes": self.has_changes,
            "exit_code": self.exit_code,
            "fail_on_changes": self.fail_on_changes,
            "structural": self.structural.to_dict(),
            "changed_node_ids": list(self.changed_node_ids),
            "changed_edge_ids": list(self.changed_edge_ids),
            "changed_snapshot_fields": list(self.changed_snapshot_fields),
        }


def build_ci_delta(
    before: GraphSnapshot,
    after: GraphSnapshot,
    *,
    fail_on_changes: bool = False,
) -> CiDeltaReport:
    """Compare canonical fact payloads for use in explicit CI jobs."""
    before_nodes = {item.id: item.to_dict() for item in before.nodes}
    after_nodes = {item.id: item.to_dict() for item in after.nodes}
    before_edges = {item.id: item.to_dict() for item in before.edges}
    after_edges = {item.id: item.to_dict() for item in after.edges}
    return CiDeltaReport(
        structural=diff_snapshots(before, after),
        changed_node_ids=tuple(
            sorted(
                item_id
                for item_id in before_nodes.keys() & after_nodes.keys()
                if before_nodes[item_id] != after_nodes[item_id]
            )
        ),
        changed_edge_ids=tuple(
            sorted(
                item_id
                for item_id in before_edges.keys() & after_edges.keys()
                if before_edges[item_id] != after_edges[item_id]
            )
        ),
        changed_snapshot_fields=tuple(
            key
            for key, before_value, after_value in (
                ("root_path", before.root_path, after.root_path),
                ("stats", dict(before.stats), dict(after.stats)),
                ("schema_version", before.schema_version, after.schema_version),
                ("indexer_version", before.indexer_version, after.indexer_version),
            )
            if before_value != after_value
        ),
        fail_on_changes=fail_on_changes,
    )


__all__ = [
    "CiDeltaReport",
    "build_ci_delta",
    "build_manifest",
    "describe_manifest_changes",
    "diff_snapshots",
    "load_manifest",
    "refresh_snapshot",
    "refresh_snapshot_incremental",
    "save_manifest",
]
