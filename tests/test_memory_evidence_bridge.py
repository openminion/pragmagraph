from __future__ import annotations

from pathlib import Path

import pytest

from pragmagraph.contracts import (
    EVIDENCE_QUERY_SUPPORT_CANDIDATE,
    FRESHNESS_CHANGED,
    FRESHNESS_FRESH,
    FRESHNESS_MISSING,
    FRESHNESS_STALE,
)
from pragmagraph.evidence import (
    collect_memory_evidence,
    collect_related_memory_evidence,
    evidence_ref_for_node,
    snapshot_evidence_id,
    verify_memory_evidence_ref,
    verify_memory_evidence_refs,
)
from pragmagraph.models import (
    GraphSnapshot,
    MemoryEvidenceBundle,
    MemoryEvidenceRef,
    PragmaGraphError,
)
from pragmagraph.refresh import refresh_snapshot

from .package_paths import build_fixture_repo


def _repo(tmp_path: Path) -> Path:
    return build_fixture_repo(
        tmp_path,
        files={
            "README.md": "# Demo\n\n## Runtime Graph\n\nFacts for memory.\n",
            "src/app.py": (
                "class RuntimeGraph:\n    def build(self):\n        return 'ready'\n"
            ),
        },
    )


def _runtime_node(snapshot: GraphSnapshot):
    return next(node for node in snapshot.nodes if node.label == "RuntimeGraph")


def test_memory_evidence_ref_and_bundle_round_trip(tmp_path: Path) -> None:
    result = refresh_snapshot(_repo(tmp_path), namespace="fixture", created_at="t0")
    ref = evidence_ref_for_node(
        result.snapshot,
        _runtime_node(result.snapshot),
        manifest=result.manifest,
    )
    bundle = MemoryEvidenceBundle(
        bundle_id="pragma://fixture/memory-evidence-bundle/demo",
        query_kind=EVIDENCE_QUERY_SUPPORT_CANDIDATE,
        refs=(ref,),
        diagnostics={"source": "test"},
    )

    assert ref.ref_uri.startswith("pragma://fixture/memory-evidence/")
    assert ref.source_ref_id.startswith("pragma://fixture/source/")
    assert ref.snapshot_id == snapshot_evidence_id(result.snapshot)
    assert ref.content_hash == result.manifest.by_path()["src/app.py"].content_hash
    assert MemoryEvidenceRef.from_dict(ref.to_dict()) == ref
    assert MemoryEvidenceBundle.from_dict(bundle.to_dict()) == bundle


def test_memory_evidence_dtos_reject_invalid_contract_values() -> None:
    with pytest.raises(PragmaGraphError) as bad_state:
        MemoryEvidenceRef(
            ref_uri="pragma://fixture/memory-evidence/ref",
            node_id="node",
            source_ref_id="source",
            snapshot_id="snapshot",
            observed_at_iso="",
            freshness_state="semantic_guess",
        )
    assert bad_state.value.code == "PRAGMAGRAPH_EVIDENCE_BAD_FRESHNESS"

    with pytest.raises(PragmaGraphError) as missing_ref:
        MemoryEvidenceRef(
            ref_uri="",
            node_id="node",
            source_ref_id="source",
            snapshot_id="snapshot",
            observed_at_iso="",
        )
    assert missing_ref.value.code == "PRAGMAGRAPH_EVIDENCE_REF_REQUIRED"

    with pytest.raises(PragmaGraphError) as bad_kind:
        MemoryEvidenceBundle(
            bundle_id="pragma://fixture/memory-evidence-bundle/demo",
            query_kind="decide_memory_quality",
        )
    assert bad_kind.value.code == "PRAGMAGRAPH_EVIDENCE_BAD_QUERY_KIND"


def test_verify_memory_evidence_reports_all_four_freshness_states(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    first = refresh_snapshot(root, namespace="fixture", created_at="t0")
    first_ref = evidence_ref_for_node(
        first.snapshot,
        _runtime_node(first.snapshot),
        manifest=first.manifest,
    )

    assert (
        verify_memory_evidence_ref(
            first_ref,
            first.snapshot,
            manifest=first.manifest,
        ).freshness_state
        == FRESHNESS_FRESH
    )

    stale_snapshot = GraphSnapshot(
        namespace=first.snapshot.namespace,
        root_path=first.snapshot.root_path,
        nodes=first.snapshot.nodes,
        edges=first.snapshot.edges,
        omitted=first.snapshot.omitted,
        stats=first.snapshot.stats,
        created_at="t1",
    )
    assert (
        verify_memory_evidence_ref(
            first_ref,
            stale_snapshot,
            manifest=first.manifest,
        ).freshness_state
        == FRESHNESS_STALE
    )

    (root / "src" / "app.py").write_text(
        "class RuntimeGraph:\n    def build(self):\n        return 'changed'\n",
        encoding="utf-8",
    )
    changed = refresh_snapshot(root, namespace="fixture", created_at="t2")
    changed_ref = verify_memory_evidence_ref(
        first_ref,
        changed.snapshot,
        manifest=changed.manifest,
    )
    assert changed_ref.freshness_state == FRESHNESS_CHANGED
    assert changed_ref.content_hash != first_ref.content_hash

    (root / "src" / "app.py").unlink()
    missing = refresh_snapshot(root, namespace="fixture", created_at="t3")
    assert (
        verify_memory_evidence_ref(
            first_ref,
            missing.snapshot,
            manifest=missing.manifest,
        ).freshness_state
        == FRESHNESS_MISSING
    )


def test_memory_evidence_query_bundles_are_structural_not_judgmental(
    tmp_path: Path,
) -> None:
    result = refresh_snapshot(_repo(tmp_path), namespace="fixture", created_at="t0")
    support = collect_memory_evidence(
        result.snapshot,
        "RuntimeGraph",
        manifest=result.manifest,
        max_results=2,
    )
    verified = verify_memory_evidence_refs(
        support.refs,
        result.snapshot,
        manifest=result.manifest,
    )
    related = collect_related_memory_evidence(
        result.snapshot,
        support.refs[0].node_id,
        manifest=result.manifest,
    )

    assert support.refs
    assert support.bundle_id.startswith("pragma://fixture/memory-evidence-bundle/")
    assert support.query_kind == EVIDENCE_QUERY_SUPPORT_CANDIDATE
    assert "memory_quality" not in support.diagnostics
    assert verified.diagnostics["fresh_count"] == str(len(support.refs))
    assert related.refs
    assert all(ref.freshness_state == FRESHNESS_FRESH for ref in related.refs)
