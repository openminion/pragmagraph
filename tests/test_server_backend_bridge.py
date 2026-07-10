from __future__ import annotations

from pathlib import Path

import pytest

from pragmagraph.server.backend import ServiceConfig, build_wired_registry
from pragmagraph.server.contracts import (
    BackendNotWiredError,
    PragmaGraphServerError,
    TOOL_UNSUPPORTED_CAPABILITY_CODE,
)
from pragmagraph.server.tools import SUPPORTED_TOOL_NAMES, ToolRegistry


def _seed_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "README.md").write_text("# Runtime Graph\n", encoding="utf-8")
    (root / "src" / "app.py").write_text(
        "class RuntimeGraph:\n"
        "    pass\n\n"
        "def build_runtime_graph():\n"
        "    return RuntimeGraph()\n",
        encoding="utf-8",
    )


def test_wired_registry_registers_exactly_the_supported_ten(tmp_path: Path):
    root = tmp_path / "repo"
    _seed_repo(root)
    registry = build_wired_registry(ServiceConfig(root_path=str(root)))
    assert registry.names() == tuple(sorted(SUPPORTED_TOOL_NAMES))


def test_wired_capabilities_reflect_root_backed_service(tmp_path: Path):
    root = tmp_path / "repo"
    _seed_repo(root)
    registry = build_wired_registry(ServiceConfig(root_path=str(root)))
    payload = registry.get_handler("pragmagraph_capabilities")()
    assert payload["service"]["startup_mode"] == "root"
    assert payload["service"]["refresh_supported"] is True


def test_wired_query_and_report_delegate_to_package_service(tmp_path: Path):
    root = tmp_path / "repo"
    _seed_repo(root)
    registry = build_wired_registry(ServiceConfig(root_path=str(root)))

    query = registry.get_handler("pragmagraph_query")(text="RuntimeGraph")
    report = registry.get_handler("pragmagraph_report")(format="json", top_n=5)

    assert query["query_result"]["hits"][0]["node"]["label"] == "RuntimeGraph"
    assert report["report"]["format"] == "json"


def test_snapshot_config_rejects_refresh_with_typed_unsupported_capability(
    tmp_path: Path,
):
    root = tmp_path / "repo"
    _seed_repo(root)
    snapshot = tmp_path / "snapshot.json"
    from pragmagraph import index_path, save_snapshot

    save_snapshot(index_path(root, namespace="fixture"), snapshot)
    registry = build_wired_registry(ServiceConfig(snapshot_path=str(snapshot)))
    with pytest.raises(PragmaGraphServerError) as excinfo:
        registry.get_handler("pragmagraph_refresh")()
    assert excinfo.value.code == TOOL_UNSUPPORTED_CAPABILITY_CODE


def test_root_backed_refresh_updates_visible_query_results(tmp_path: Path):
    root = tmp_path / "repo"
    _seed_repo(root)
    registry = build_wired_registry(
        ServiceConfig(
            root_path=str(root),
            namespace="fixture",
            snapshot_out=str(tmp_path / "snapshot.json"),
            manifest_out=str(tmp_path / "manifest.json"),
            state_out=str(tmp_path / "state.json"),
        )
    )
    initial = registry.get_handler("pragmagraph_query")(text="OperatorGraph")
    assert initial["query_result"]["hits"] == []

    (root / "src" / "ops.py").write_text("class OperatorGraph:\n    pass\n")
    refreshed = registry.get_handler("pragmagraph_refresh")()
    queried = registry.get_handler("pragmagraph_query")(text="OperatorGraph")

    assert "src/ops.py" in refreshed["refresh"]["changed_paths"]
    assert queried["query_result"]["hits"][0]["node"]["label"] == "OperatorGraph"


def test_stub_registry_still_raises_backend_not_wired_when_explicit():
    stub_registry = ToolRegistry.default()
    handler = stub_registry.get_handler("pragmagraph_query")
    with pytest.raises(BackendNotWiredError):
        handler(text="anything")


def test_invalid_service_config_requires_exactly_one_startup_source():
    with pytest.raises(PragmaGraphServerError):
        ServiceConfig()
