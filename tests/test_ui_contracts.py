from __future__ import annotations

import json
from threading import Thread
from urllib.request import urlopen

import pytest


def test_ui_import_root_and_boundary_contract_are_stable() -> None:
    from pragmagraph import ui

    boundary = ui.build_default_ui_boundary()
    assert boundary.owner_import_root == "pragmagraph.ui"
    assert boundary.runtime_package == "openminion"
    assert boundary.transport == "openminion_workbench"
    assert boundary.transport_status == "planned_not_implemented"
    assert boundary.local_preview_status == "available"
    assert boundary.ui_owner_surface == "openminion third-brain workbench"
    assert boundary.api_surface == "openminion third-brain adapter layer"
    assert boundary.imports_openminion is False
    assert boundary.imports_runtime_package is False


def test_ui_screen_manifest_covers_workbench_mvp_routes() -> None:
    from pragmagraph.ui import build_ui_screen_manifest

    screens = build_ui_screen_manifest()
    assert [screen.screen_id for screen in screens] == [
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
        "project_health",
        "evidence",
        "delta_review",
        "investigation",
        "graph_pack_review",
    ]
    assert [screen.screen_id for screen in screens if screen.mvp] == [
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
        "project_health",
        "evidence",
        "delta_review",
        "investigation",
        "graph_pack_review",
    ]
    assert [screen.screen_id for screen in screens if screen.mutating] == [
        "provider_status"
    ]


def test_ui_local_visual_server_is_reusable_for_pragmagraph_renderers() -> None:
    from pragmagraph.ui import make_local_visual_server

    try:
        server = make_local_visual_server(
            render_path=lambda path, query: (
                "<!doctype html><title>PragmaGraph</title>"
                f"<main data-path='{path}'>{query.get('q', [''])[0]}</main>"
            ),
            default_path="/search",
            port=0,
        )
    except PermissionError:
        pytest.skip("local socket binding is unavailable in this sandbox")
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"{server.preview_url}?q=RuntimeGraph", timeout=5) as response:
            html = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert "/search" in server.preview_url
    assert "PragmaGraph" in html
    assert "RuntimeGraph" in html


def test_ui_preview_exports_match_sophiagraph_local_visual_pattern() -> None:
    from pragmagraph.ui import UiPreviewRequest, render_ui_preview

    rendered = render_ui_preview(
        UiPreviewRequest(screen="search", query="RuntimeGraph")
    )

    assert rendered.screen == "search"
    assert rendered.node_count == 4
    assert "GraphFakos" in rendered.html
    assert "PragmaGraph" in rendered.html
    assert "Graph Canvas" in rendered.html
    assert "Provider Status" in rendered.html
    assert "PragmaGraph Observed Source Graph" in rendered.html


def test_ui_investigation_preview_carries_guided_payload(tmp_path) -> None:
    from pragmagraph.adapters import index_path
    from pragmagraph.storage import save_snapshot
    from pragmagraph.ui import UiPreviewRequest, write_ui_preview

    from .package_paths import build_fixture_repo

    root = build_fixture_repo(
        tmp_path,
        files={"src/app.py": "class RuntimeGraph:\n    pass\n"},
    )
    snapshot_path = tmp_path / "snapshot.json"
    artifact_path = tmp_path / "investigation-artifact.json"
    save_snapshot(index_path(root, namespace="ui-investigation"), snapshot_path)

    result = write_ui_preview(
        UiPreviewRequest(
            screen="investigation",
            snapshot=str(snapshot_path),
            query="RuntimeGraph",
            investigation_preset="symbol_map",
            output_path=str(tmp_path / "investigation.html"),
            artifact_path=str(artifact_path),
        )
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert result.investigation is not None
    assert result.investigation["schema_version"] == (
        "pragmagraph.investigation.v1alpha1"
    )
    assert result.investigation["boundary"] == "observed_facts_only"
    assert result.investigation["matches"][0]["label"] == "RuntimeGraph"
    assert artifact["provider_payload"]["investigation"]["preset"] == "symbol_map"


def test_ui_graph_pack_review_preview_carries_receive_payload(tmp_path) -> None:
    from pragmagraph.adapters import index_path
    from pragmagraph.portability import write_graph_pack
    from pragmagraph.ui import UiPreviewRequest, write_ui_preview

    from .package_paths import build_fixture_repo

    root = build_fixture_repo(
        tmp_path,
        files={"src/app.py": "class RuntimeGraph:\n    pass\n"},
    )
    snapshot = index_path(root, namespace="ui-pack")
    pack_dir = tmp_path / "graph-pack"
    artifact_path = tmp_path / "graph-pack-artifact.json"
    write_graph_pack(snapshot, pack_dir, include_store=True)

    result = write_ui_preview(
        UiPreviewRequest(
            screen="graph_pack_review",
            graph_pack_path=str(pack_dir),
            snapshot_out=str(tmp_path / "imported-snapshot.json"),
            store_out=str(tmp_path / "imported.sqlite"),
            output_path=str(tmp_path / "graph-pack.html"),
            artifact_path=str(artifact_path),
        )
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert result.graph_pack_review is not None
    assert result.graph_pack_review["schema_version"] == (
        "pragmagraph.ui_graph_pack_review.v1alpha1"
    )
    review = result.graph_pack_review["review"]
    assert review["receive_summary"]["ready_to_import"] is True
    assert artifact["provider_payload"]["graph_pack_review"]["mode"] == (
        "receive_review"
    )


def test_ui_preview_includes_snapshot_service_status(tmp_path) -> None:
    from pragmagraph.adapters import index_path
    from pragmagraph.storage import save_snapshot
    from pragmagraph.ui import UiPreviewRequest, render_ui_preview

    from .package_paths import build_fixture_repo

    root = build_fixture_repo(
        tmp_path,
        files={"src/app.py": "class RuntimeGraph:\n    pass\n"},
    )
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(index_path(root, namespace="ui-status"), snapshot_path)

    rendered = render_ui_preview(
        UiPreviewRequest(screen="provider_status", snapshot=str(snapshot_path))
    )

    assert "PragmaGraph Observed Source Graph" in rendered.html
    assert "snapshot_backed_refresh_unsupported" in rendered.html


def test_ui_evidence_preview_exports_store_proof_and_agent_context(tmp_path) -> None:
    from pragmagraph.adapters import index_path
    from pragmagraph.storage import SQLiteGraphStore, save_snapshot
    from pragmagraph.ui import UiPreviewRequest, write_ui_preview

    from .package_paths import build_fixture_repo

    root = build_fixture_repo(
        tmp_path,
        files={"src/app.py": "class RuntimeGraph:\n    pass\n"},
    )
    snapshot = index_path(root, namespace="ui-evidence")
    snapshot_path = tmp_path / "snapshot.json"
    store_path = tmp_path / "graph.sqlite"
    evidence_path = tmp_path / "evidence.json"
    context_path = tmp_path / "agent-context.md"
    save_snapshot(snapshot, snapshot_path)
    SQLiteGraphStore.from_snapshot(snapshot, store_path)

    result = write_ui_preview(
        UiPreviewRequest(
            screen="evidence",
            snapshot=str(snapshot_path),
            store_path=str(store_path),
            query="RuntimeGraph",
            output_path=str(tmp_path / "evidence.html"),
            artifact_path=str(tmp_path / "artifact.json"),
            evidence_path=str(evidence_path),
            agent_context_path=str(context_path),
        )
    )

    assert result.evidence == {
        "evidence": True,
        "output_path": str(evidence_path),
    }
    assert result.agent_context == {
        "agent_context": True,
        "output_path": str(context_path),
    }
    evidence = evidence_path.read_text(encoding="utf-8")
    context = context_path.read_text(encoding="utf-8")
    assert "pragmagraph.evidence_workbench.v1alpha1" in evidence
    assert "existing_store_export_compare" in evidence
    assert "materialized_store" in evidence
    assert "PragmaGraph Agent Context" in context
    assert "RuntimeGraph" in context
