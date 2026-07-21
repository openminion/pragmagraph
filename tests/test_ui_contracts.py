from __future__ import annotations

from threading import Thread
from urllib.request import urlopen

import pytest


def test_ui_import_root_and_boundary_contract_are_stable() -> None:
    import pragmagraph.ui as ui

    boundary = ui.build_default_ui_boundary()
    assert boundary.owner_import_root == "pragmagraph.ui"
    assert boundary.runtime_package == "openminion"
    assert boundary.transport == "openminion_workbench"
    assert boundary.transport_status == "planned_not_implemented"
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
    ]
    assert [screen.screen_id for screen in screens if screen.mvp] == [
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
        "project_health",
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
