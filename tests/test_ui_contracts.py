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
    ]
    assert [screen.screen_id for screen in screens if screen.mvp] == [
        "search",
        "result_detail",
        "neighborhood",
        "path",
        "provider_status",
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
    assert "OpenMinion Integration" in rendered.html
    assert "Third-brain observed source graph." in rendered.html
