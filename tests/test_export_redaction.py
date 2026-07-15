from __future__ import annotations

from pragmagraph.export import project_snapshot
from pragmagraph.models import GraphEdge, GraphNode, GraphSnapshot, SourceRef
from pragmagraph.service import LocalQueryService, ServiceRequest, ServiceStartup


def _snapshot() -> GraphSnapshot:
    node = GraphNode(
        id="node:one",
        kind="git_commit",
        label="private subject",
        text="private content",
        source_ref=SourceRef(path="src/private.py"),
        metadata={
            "author_name": "Ada",
            "author_email": "ada@example.com",
            "subject": "private subject",
            "safe": "kept",
        },
    )
    edge = GraphEdge(
        id="edge:self",
        kind="mentions",
        source_id=node.id,
        target_id=node.id,
        metadata={"committer_email_hash": "hash", "safe": "kept"},
    )
    return GraphSnapshot(
        namespace="redaction",
        root_path="/private/repo",
        nodes=(node,),
        edges=(edge,),
    )


def test_export_profiles_do_not_mutate_canonical_snapshot() -> None:
    original = _snapshot()
    content = project_snapshot(original, profile="no_content")
    identities = project_snapshot(original, profile="no_identities")
    portable = project_snapshot(original, profile="portable")

    assert content.snapshot.nodes[0].text == ""
    assert content.snapshot.nodes[0].label == "git_commit"
    assert "subject" not in content.snapshot.nodes[0].metadata
    assert "author_email" not in identities.snapshot.nodes[0].metadata
    assert "committer_email_hash" not in identities.snapshot.edges[0].metadata
    assert portable.snapshot.root_path == ""
    assert portable.snapshot.nodes[0].source_ref.path == "src/private.py"
    assert original.nodes[0].text == "private content"
    assert original.root_path == "/private/repo"


def test_export_projection_preserves_referential_integrity() -> None:
    projection = project_snapshot(_snapshot(), profile="no_identities")
    node_ids = {node.id for node in projection.snapshot.nodes}

    assert all(
        edge.source_id in node_ids and edge.target_id in node_ids
        for edge in projection.snapshot.edges
    )
    assert projection.redacted_fields == (
        "metadata.author_email",
        "metadata.author_name",
        "metadata.committer_email_hash",
    )


def test_service_export_applies_requested_profile() -> None:
    service = LocalQueryService(
        snapshot=_snapshot(),
        startup=ServiceStartup(mode="snapshot", namespace="redaction"),
    )

    response, _ = service.handle_request(
        ServiceRequest(
            id="export",
            method="export",
            params={"format": "dot", "profile": "no_content"},
        )
    )

    assert response.ok is True
    assert response.result["profile"] == "no_content"
    assert "private subject" not in response.result["text"]

    invalid, _ = service.handle_request(
        ServiceRequest(
            id="invalid-export",
            method="export",
            params={"format": "dot", "profile": "secret"},
        )
    )
    assert invalid.ok is False
    assert invalid.error.code == "invalid_params"
