"""Memory evidence bridge over deterministic PragmaGraph snapshots."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from pragmagraph.contracts import (
    EVIDENCE_QUERY_COLLECT_RELATED,
    EVIDENCE_QUERY_SUPPORT_CANDIDATE,
    EVIDENCE_QUERY_VERIFY_CITATION,
    FRESHNESS_CHANGED,
    FRESHNESS_FRESH,
    FRESHNESS_MISSING,
    FRESHNESS_STALE,
)
from pragmagraph.models import (
    GraphNode,
    GraphSnapshot,
    MemoryEvidenceBundle,
    MemoryEvidenceRef,
    QueryRequest,
    RefreshManifest,
)
from pragmagraph.portability import pragma_uri
from pragmagraph.query import neighborhood, query
from pragmagraph.storage import stable_dumps


def snapshot_evidence_id(snapshot: GraphSnapshot) -> str:
    """Return the stable short snapshot identifier used by evidence refs."""
    return hashlib.sha256(stable_dumps(snapshot).encode("utf-8")).hexdigest()[:16]


def evidence_ref_for_node(
    snapshot: GraphSnapshot,
    node: GraphNode,
    *,
    manifest: RefreshManifest | None = None,
    freshness_state: str = FRESHNESS_FRESH,
) -> MemoryEvidenceRef:
    """Build a source-backed evidence ref for one observed graph node."""
    source_ref_id = _source_ref_id(snapshot, node)
    snapshot_id = snapshot_evidence_id(snapshot)
    content_hash = _content_hash_for_node(node, manifest)
    return MemoryEvidenceRef(
        ref_uri=pragma_uri(
            snapshot.namespace, "memory-evidence", f"{snapshot_id}/{node.id}"
        ),
        node_id=node.id,
        source_ref_id=source_ref_id,
        snapshot_id=snapshot_id,
        observed_at_iso=snapshot.created_at,
        freshness_state=freshness_state,
        content_hash=content_hash,
    )


def verify_memory_evidence_ref(
    ref: MemoryEvidenceRef,
    snapshot: GraphSnapshot,
    *,
    manifest: RefreshManifest | None = None,
) -> MemoryEvidenceRef:
    """Re-check one evidence ref against a current snapshot and manifest."""
    node = snapshot.node_map().get(ref.node_id)
    if node is None:
        return _ref_with_state(ref, FRESHNESS_MISSING)
    current_hash = _content_hash_for_node(node, manifest)
    if ref.content_hash and current_hash is None:
        return _ref_with_state(ref, FRESHNESS_MISSING)
    if ref.content_hash and current_hash != ref.content_hash:
        return _ref_with_state(ref, FRESHNESS_CHANGED, content_hash=current_hash)
    if ref.snapshot_id != snapshot_evidence_id(snapshot):
        return _ref_with_state(ref, FRESHNESS_STALE, content_hash=current_hash)
    return _ref_with_state(ref, FRESHNESS_FRESH, content_hash=current_hash)


def verify_memory_evidence_refs(
    refs: Iterable[MemoryEvidenceRef],
    snapshot: GraphSnapshot,
    *,
    manifest: RefreshManifest | None = None,
) -> MemoryEvidenceBundle:
    """Return a verification bundle for existing PragmaGraph evidence refs."""
    verified = tuple(
        verify_memory_evidence_ref(ref, snapshot, manifest=manifest) for ref in refs
    )
    omitted = tuple(
        f"evidence_{ref.freshness_state}"
        for ref in verified
        if ref.freshness_state != FRESHNESS_FRESH
    )
    return MemoryEvidenceBundle(
        bundle_id=_bundle_id(
            snapshot,
            EVIDENCE_QUERY_VERIFY_CITATION,
            tuple(ref.ref_uri for ref in verified),
        ),
        query_kind=EVIDENCE_QUERY_VERIFY_CITATION,
        refs=verified,
        omitted_reason_codes=omitted,
        diagnostics=_state_counts(verified),
    )


def collect_memory_evidence(
    snapshot: GraphSnapshot,
    query_text: str,
    *,
    manifest: RefreshManifest | None = None,
    max_results: int = 10,
) -> MemoryEvidenceBundle:
    """Collect deterministic source evidence supporting a memory candidate."""
    result = query(snapshot, QueryRequest(query=query_text, max_results=max_results))
    refs = tuple(
        evidence_ref_for_node(snapshot, hit.node, manifest=manifest)
        for hit in result.hits[:max_results]
    )
    return MemoryEvidenceBundle(
        bundle_id=_bundle_id(
            snapshot,
            EVIDENCE_QUERY_SUPPORT_CANDIDATE,
            (query_text, str(max_results), *(ref.ref_uri for ref in refs)),
        ),
        query_kind=EVIDENCE_QUERY_SUPPORT_CANDIDATE,
        refs=refs,
        omitted_reason_codes=tuple(item.reason for item in result.omitted),
        diagnostics={"query": query_text, "hit_count": str(len(refs))},
    )


def collect_related_memory_evidence(
    snapshot: GraphSnapshot,
    node_id: str,
    *,
    manifest: RefreshManifest | None = None,
    depth: int = 1,
    max_results: int = 10,
) -> MemoryEvidenceBundle:
    """Collect deterministic neighboring evidence around one cited node."""
    result = neighborhood(
        snapshot,
        node_id,
        depth=depth,
        max_results=max_results,
    )
    refs = tuple(
        evidence_ref_for_node(snapshot, hit.node, manifest=manifest)
        for hit in result.hits
    )
    return MemoryEvidenceBundle(
        bundle_id=_bundle_id(
            snapshot,
            EVIDENCE_QUERY_COLLECT_RELATED,
            (node_id, str(depth), str(max_results), *(ref.ref_uri for ref in refs)),
        ),
        query_kind=EVIDENCE_QUERY_COLLECT_RELATED,
        refs=refs,
        omitted_reason_codes=tuple(item.reason for item in result.omitted),
        diagnostics={"node_id": node_id, "hit_count": str(len(refs))},
    )


def _source_ref_id(snapshot: GraphSnapshot, node: GraphNode) -> str:
    ref = node.source_ref
    if ref.uri:
        return ref.uri
    key_parts = [ref.path or node.id]
    if ref.section:
        key_parts.append(f"section={ref.section}")
    if ref.line is not None:
        key_parts.append(f"line={ref.line}")
    if ref.column is not None:
        key_parts.append(f"column={ref.column}")
    return pragma_uri(snapshot.namespace, "source", "#".join(key_parts))


def _content_hash_for_node(
    node: GraphNode,
    manifest: RefreshManifest | None,
) -> str | None:
    if manifest is None or not node.source_ref.path:
        return None
    entry = manifest.by_path().get(node.source_ref.path)
    return None if entry is None else entry.content_hash


def _ref_with_state(
    ref: MemoryEvidenceRef,
    freshness_state: str,
    *,
    content_hash: str | None = None,
) -> MemoryEvidenceRef:
    return MemoryEvidenceRef(
        ref_uri=ref.ref_uri,
        node_id=ref.node_id,
        source_ref_id=ref.source_ref_id,
        snapshot_id=ref.snapshot_id,
        observed_at_iso=ref.observed_at_iso,
        freshness_state=freshness_state,
        content_hash=content_hash if content_hash is not None else ref.content_hash,
    )


def _bundle_id(
    snapshot: GraphSnapshot,
    query_kind: str,
    parts: tuple[str, ...],
) -> str:
    digest = hashlib.sha256(
        "\n".join((snapshot_evidence_id(snapshot), query_kind, *parts)).encode("utf-8")
    ).hexdigest()[:16]
    return pragma_uri(snapshot.namespace, "memory-evidence-bundle", digest)


def _state_counts(refs: tuple[MemoryEvidenceRef, ...]) -> dict[str, str]:
    counts: dict[str, int] = {}
    for ref in refs:
        counts[ref.freshness_state] = counts.get(ref.freshness_state, 0) + 1
    return {f"{state}_count": str(count) for state, count in sorted(counts.items())}


__all__ = [
    "collect_memory_evidence",
    "collect_related_memory_evidence",
    "evidence_ref_for_node",
    "snapshot_evidence_id",
    "verify_memory_evidence_ref",
    "verify_memory_evidence_refs",
]
