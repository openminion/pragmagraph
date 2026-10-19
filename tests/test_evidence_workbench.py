from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pragmagraph.__main__ import main
from pragmagraph.adapters import index_path
from pragmagraph.models import QueryRequest
from pragmagraph.query import query
from pragmagraph.storage import SQLiteGraphStore, load_snapshot, save_snapshot
from pragmagraph.ui import UiPreviewRequest, build_evidence_payload
from pragmagraph.ui.preview_inputs import demo_snapshot
from pragmagraph.workspace import (
    WorkspaceConfig,
    initialize_workspace,
    save_workspace_config,
)

from .package_paths import build_fixture_repo


def _fixture_snapshot(tmp_path: Path):
    root = build_fixture_repo(
        tmp_path,
        repo_name="evidence-repo",
        files={
            "README.md": "# Evidence\n\nSee `src/app.py`.\n",
            "src/app.py": "class RuntimeGraph:\n    pass\n",
        },
    )
    return index_path(root, namespace="evidence")


def test_evidence_payload_combines_status_search_store_and_agent_context(
    tmp_path: Path,
) -> None:
    snapshot = _fixture_snapshot(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    store_path = tmp_path / "graph.sqlite"
    save_snapshot(snapshot, snapshot_path)
    SQLiteGraphStore.from_snapshot(snapshot, store_path)

    payload = build_evidence_payload(
        snapshot,
        UiPreviewRequest(
            screen="evidence",
            snapshot=str(snapshot_path),
            store_path=str(store_path),
            query="RuntimeGraph",
        ),
    )

    assert payload["schema_version"] == "pragmagraph.evidence_workbench.v1alpha1"
    assert payload["boundary"] == "observed_facts_only"
    assert payload["service_status"]["startup_mode"] == "snapshot"
    assert payload["search_explanation"]["mode"] == "materialized_store"
    assert payload["store_round_trip"]["ok"] is True
    assert payload["store_round_trip"]["mode"] == "existing_store_export_compare"
    assert payload["agent_context"]["schema_version"] == (
        "pragmagraph.agent_context.v1alpha1"
    )
    assert payload["agent_context"]["top_hits"]


def test_doctor_command_writes_evidence_and_agent_context(tmp_path: Path) -> None:
    snapshot = _fixture_snapshot(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    store_path = tmp_path / "graph.sqlite"
    evidence_path = tmp_path / "doctor-evidence.json"
    context_path = tmp_path / "doctor-context.md"
    save_snapshot(snapshot, snapshot_path)
    SQLiteGraphStore.from_snapshot(snapshot, store_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pragmagraph",
            "doctor",
            "--snapshot",
            str(snapshot_path),
            "--store",
            str(store_path),
            "--query",
            "RuntimeGraph",
            "--evidence-out",
            str(evidence_path),
            "--agent-context-out",
            str(context_path),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    context = context_path.read_text(encoding="utf-8")
    assert payload["evidence"]["store_round_trip"]["ok"] is True
    assert payload["evidence_output_path"] == str(evidence_path)
    assert payload["agent_context_output_path"] == str(context_path)
    assert evidence["search_explanation"]["mode"] == "materialized_store"
    assert "PragmaGraph Agent Context" in context


@pytest.mark.parametrize("source", ["demo", "snapshot", "store", "workspace"])
@pytest.mark.parametrize("requested_query", [None, "", "NoMatch"])
def test_doctor_query_defaults_and_overrides(tmp_path, capsys, source, requested_query):
    snapshot = demo_snapshot() if source == "demo" else _fixture_snapshot(tmp_path)
    args = ["doctor", "--json"]
    if source == "snapshot":
        path = save_snapshot(snapshot, tmp_path / "snapshot.json")
        args.extend(["--snapshot", str(path)])
    elif source == "store":
        path = tmp_path / "graph.sqlite"
        SQLiteGraphStore.from_snapshot(snapshot, path)
        args.extend(["--store-only", str(path)])
    elif source == "workspace":
        path = tmp_path / "workspace"
        initialize_workspace(
            label="test", root_path=snapshot.root_path, workspace_path=path
        )
        snapshot = load_snapshot(path / "snapshot.json")
        args.extend(["--workspace", str(path)])
    if requested_query is not None:
        args.extend(["--query", requested_query])

    assert main(args) == 0
    evidence = json.loads(capsys.readouterr().out)["evidence"]
    expected = "RuntimeGraph" if requested_query is None else requested_query

    assert evidence["query"] == expected
    assert evidence["agent_context"]["query"] == expected
    assert (
        evidence["query_result"]["hits"]
        == query(snapshot, QueryRequest(query=expected, max_results=5)).to_dict()[
            "hits"
        ]
    )


@pytest.mark.parametrize("saved_query", ["RuntimeGraph", ""])
@pytest.mark.parametrize("requested_query", [None, "", "NoMatch"])
def test_doctor_config_query_is_overridden_only_when_explicit(
    tmp_path, capsys, saved_query, requested_query
):
    snapshot = _fixture_snapshot(tmp_path)
    workspace = tmp_path / "workspace"
    config_path = save_workspace_config(
        WorkspaceConfig(
            root_path=snapshot.root_path,
            workspace_path=str(workspace),
            ui_query=saved_query,
        ),
        tmp_path / "workspace.toml",
    )
    original_config = config_path.read_bytes()
    args = ["doctor", "--config", str(config_path), "--json"]
    if requested_query is not None:
        args.extend(["--query", requested_query])

    assert main(args) == 0
    evidence = json.loads(capsys.readouterr().out)["evidence"]
    expected = saved_query if requested_query is None else requested_query

    assert evidence["query"] == expected
    assert evidence["agent_context"]["query"] == expected
    assert (
        evidence["query_result"]["hits"]
        == query(
            load_snapshot(workspace / "snapshot.json"),
            QueryRequest(query=expected, max_results=5),
        ).to_dict()["hits"]
    )
    assert config_path.read_bytes() == original_config
