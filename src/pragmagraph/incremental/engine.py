"""Changed-file extraction and deterministic cache assembly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pragmagraph.adapters import (
    assemble_snapshot,
    collect_index_entries,
    extract_file_fragment,
)
from pragmagraph.contracts import (
    EDGE_GIT_CHANGES_PATH,
    EDGE_GIT_PARENT,
    EDGE_GIT_TOUCHES,
    NODE_FILE,
    NODE_GIT_CHANGED_PATH,
    NODE_GIT_COMMIT,
)
from pragmagraph.incremental.cache import build_cache_fingerprint
from pragmagraph.incremental.models import (
    CacheFingerprint,
    ExtractionCacheBundle,
    FileIndexFragment,
)
from pragmagraph.models import (
    GraphSnapshot,
    IdentityTransition,
    RefreshManifest,
    RefreshWorkStats,
)
from pragmagraph.parsers import ParserRegistry
from pragmagraph.portability import normalize_relative_path
from pragmagraph.security import ScopePolicy


_GIT_NODE_KINDS = frozenset({NODE_GIT_COMMIT, NODE_GIT_CHANGED_PATH})
_GIT_EDGE_KINDS = frozenset({EDGE_GIT_CHANGES_PATH, EDGE_GIT_PARENT, EDGE_GIT_TOUCHES})


@dataclass(frozen=True)
class IncrementalBuild:
    """Internal output needed to complete one refresh result."""

    snapshot: GraphSnapshot
    cache: ExtractionCacheBundle
    work: RefreshWorkStats
    identity_transitions: tuple[IdentityTransition, ...] = ()


def build_incremental_snapshot(
    root_path: str | Path,
    *,
    namespace: str,
    manifest: RefreshManifest,
    previous_snapshot: GraphSnapshot | None,
    previous_cache: ExtractionCacheBundle | None,
    policy: ScopePolicy,
    parser_registry: ParserRegistry,
    created_at: str,
    git_identity_mode: str,
) -> IncrementalBuild:
    """Build a snapshot by reusing compatible unchanged file fragments."""
    root = Path(root_path).resolve()
    entries = collect_index_entries(root, policy=policy)
    fingerprint = build_cache_fingerprint(
        root,
        namespace=namespace,
        policy=policy,
        parser_registry=parser_registry,
        manifest=manifest,
        git_identity_mode=git_identity_mode,
    )
    extraction_compatible, git_compatible = _cache_compat(previous_cache, fingerprint)
    cached = previous_cache.by_path() if previous_cache is not None else {}
    manifest_by_path = manifest.by_path()
    fragments: dict[str, FileIndexFragment] = {}
    parsed_count = 0
    reused_count = 0
    for path, diagnostic in entries:
        if diagnostic is not None or not path.is_file():
            continue
        rel = normalize_relative_path(path.relative_to(root))
        manifest_entry = manifest_by_path[rel]
        prior = cached.get(rel) if extraction_compatible else None
        if (
            prior is not None
            and prior.content_hash == manifest_entry.content_hash
            and prior.parser == manifest_entry.parser
            and prior.parser_version == manifest_entry.parser_version
        ):
            fragments[rel] = prior
            reused_count += 1
            continue
        fragments[rel] = extract_file_fragment(
            root,
            path,
            namespace=namespace,
            parser_registry=parser_registry,
        )
        parsed_count += 1
    cached_overlay = None
    if git_compatible:
        cached_overlay = (
            previous_cache.git_nodes,
            previous_cache.git_edges,
            previous_cache.git_omitted,
            previous_cache.git_stats,
        )
    snapshot = assemble_snapshot(
        root,
        namespace=namespace,
        entries=entries,
        fragments=fragments,
        created_at=created_at,
        parser_registry=parser_registry,
        git_identity_mode=git_identity_mode,
        scope_policy=policy,
        cached_git_overlay=cached_overlay,
    )
    git_nodes, git_edges, git_omitted, git_stats = _git_overlay_from_snapshot(snapshot)
    cache = ExtractionCacheBundle(
        fingerprint=fingerprint,
        fragments=tuple(fragments.values()),
        git_nodes=git_nodes,
        git_edges=git_edges,
        git_omitted=git_omitted,
        git_stats=git_stats,
    )
    fallback_reason = ""
    if previous_cache is None:
        fallback_reason = "cache_missing"
    elif not extraction_compatible:
        fallback_reason = "cache_incompatible"
    return IncrementalBuild(
        snapshot=snapshot,
        cache=cache,
        work=RefreshWorkStats(
            strategy="incremental",
            paths_walked=len({str(path) for path, _ in entries}),
            source_bytes_hashed=sum(entry.size_bytes for entry in manifest.entries),
            parsed_path_count=parsed_count,
            reused_path_count=reused_count,
            resolution_overlay_rebuilt=True,
            git_overlay_rebuilt=not git_compatible,
            cache_fallback_reason=fallback_reason,
        ),
        identity_transitions=_identity_transitions(previous_snapshot, snapshot),
    )


def _cache_compat(
    previous_cache: ExtractionCacheBundle | None,
    fingerprint: CacheFingerprint,
) -> tuple[bool, bool]:
    if previous_cache is None:
        return False, False
    previous = previous_cache.fingerprint
    return (
        previous.extraction_key() == fingerprint.extraction_key(),
        previous.git_key() == fingerprint.git_key(),
    )


def _git_overlay_from_snapshot(
    snapshot: GraphSnapshot,
) -> tuple[tuple, tuple, tuple, dict[str, object]]:
    git_nodes = tuple(node for node in snapshot.nodes if node.kind in _GIT_NODE_KINDS)
    git_edges = tuple(edge for edge in snapshot.edges if edge.kind in _GIT_EDGE_KINDS)
    git_omitted = tuple(
        item for item in snapshot.omitted if item.reason.startswith("git_")
    )
    git_stats = {
        key: value for key, value in snapshot.stats.items() if key.startswith("git_")
    }
    return git_nodes, git_edges, git_omitted, git_stats


def _identity_transitions(
    previous: GraphSnapshot | None,
    current: GraphSnapshot,
) -> tuple[IdentityTransition, ...]:
    if previous is None:
        return ()
    previous_by_path = _nodes_by_path(previous)
    current_by_path = _nodes_by_path(current)
    transitions: dict[tuple[str, str], IdentityTransition] = {}
    for node in current.nodes:
        if node.kind != NODE_GIT_CHANGED_PATH:
            continue
        previous_path = str(node.metadata.get("previous_path", "") or "")
        current_path = node.source_ref.path
        if not previous_path or not current_path:
            continue
        before = previous_by_path.get(previous_path, ())
        after = current_by_path.get(current_path, ())
        _add_transition_matches(
            transitions,
            before,
            after,
            previous_path=previous_path,
            current_path=current_path,
        )
    return tuple(
        sorted(
            transitions.values(),
            key=lambda item: (item.previous_id, item.current_id),
        )
    )


def _nodes_by_path(snapshot: GraphSnapshot) -> dict[str, tuple]:
    grouped: dict[str, list] = {}
    for node in snapshot.nodes:
        if node.source_ref.path:
            grouped.setdefault(node.source_ref.path, []).append(node)
    return {key: tuple(value) for key, value in grouped.items()}


def _add_transition_matches(
    transitions: dict[tuple[str, str], IdentityTransition],
    before: tuple,
    after: tuple,
    *,
    previous_path: str,
    current_path: str,
) -> None:
    previous_files = [node for node in before if node.kind == NODE_FILE]
    current_files = [node for node in after if node.kind == NODE_FILE]
    if len(previous_files) == len(current_files) == 1:
        _record_transition(
            transitions,
            previous_files[0],
            current_files[0],
            previous_path,
            current_path,
        )
    for prior in before:
        if prior.kind == NODE_FILE:
            continue
        matches = [
            node
            for node in after
            if node.kind == prior.kind and node.label == prior.label
        ]
        if len(matches) == 1:
            _record_transition(
                transitions,
                prior,
                matches[0],
                previous_path,
                current_path,
            )


def _record_transition(
    transitions: dict[tuple[str, str], IdentityTransition],
    previous: object,
    current: object,
    previous_path: str,
    current_path: str,
) -> None:
    previous_id = getattr(previous, "id")
    current_id = getattr(current, "id")
    if previous_id == current_id:
        return
    transition = IdentityTransition(
        previous_id=previous_id,
        current_id=current_id,
        kind=getattr(current, "kind"),
        previous_path=previous_path,
        current_path=current_path,
    )
    transitions[(previous_id, current_id)] = transition


__all__ = ["IncrementalBuild", "build_incremental_snapshot"]
