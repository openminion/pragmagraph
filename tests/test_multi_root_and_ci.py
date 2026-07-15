from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from pragmagraph.models import GraphNode, GraphSnapshot, PragmaGraphError
from pragmagraph.refresh import build_ci_delta
from pragmagraph.storage import stable_dumps
from pragmagraph.workspace import WorkspaceRoot, index_multi_root


def test_multi_root_index_is_order_independent_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    api = tmp_path / "api"
    web = tmp_path / "web"
    api.mkdir()
    web.mkdir()
    (api / "service.py").write_text("def serve():\n    return 1\n")
    (web / "client.ts").write_text("export function load() { return 1 }\n")
    roots = (WorkspaceRoot("api", str(api)), WorkspaceRoot("web", str(web)))

    first = index_multi_root(roots)
    second = index_multi_root(reversed(roots))

    assert stable_dumps(first) == stable_dumps(second)
    assert first.stats["root_names"] == ("api", "web")
    assert {node.metadata.get("workspace_root") for node in first.nodes} >= {
        "api",
        "web",
    }


def test_multi_root_rejects_duplicate_namespaces(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(PragmaGraphError) as exc:
        index_multi_root(
            (
                WorkspaceRoot("one", str(root), namespace="shared"),
                WorkspaceRoot("two", str(root), namespace="shared"),
            )
        )
    assert exc.value.code == "DUPLICATE_ROOT_NAMESPACE"


def test_ci_delta_reports_payload_changes_and_exit_policy() -> None:
    node = GraphNode(id="node:1", kind="file", label="one")
    before = GraphSnapshot(namespace="ci", root_path=".", nodes=(node,))
    after = replace(before, nodes=(replace(node, label="two"),))

    report = build_ci_delta(before, after, fail_on_changes=True)

    assert report.changed_node_ids == ("node:1",)
    assert report.structural.added_node_ids == ()
    assert report.has_changes is True
    assert report.exit_code == 1
