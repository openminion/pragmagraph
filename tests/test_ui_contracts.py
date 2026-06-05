from __future__ import annotations


def test_ui_import_root_and_boundary_contract_are_stable() -> None:
    import pragmagraph.ui as ui

    boundary = ui.build_default_ui_boundary()
    assert boundary.owner_import_root == "pragmagraph.ui"
    assert boundary.runtime_package == "openminion"
    assert boundary.transport == "openminion_workbench"
    assert boundary.transport_status == "planned_not_implemented"
    assert boundary.ui_owner_surface == "openminion third-brain workbench"
    assert boundary.api_surface == "openminion.modules.knowledge_graphs"
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
