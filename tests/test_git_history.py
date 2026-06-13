from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from pragmagraph.adapters import index_path
from pragmagraph.models import GraphNode
from pragmagraph.query import (
    commits_touching_symbol_file,
    files_touched_by_commit,
    recent_commits_for_path,
)
from pragmagraph.report import build_report, render_markdown_report
from pragmagraph.service import LocalQueryService, ServiceRequest
from pragmagraph.storage import save_snapshot, stable_dumps


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    full_env = dict(os.environ)
    full_env.setdefault("LC_ALL", "C")
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env=full_env,
    ).stdout.strip()


def _commit_env(
    *,
    name: str,
    email: str,
    date: str,
) -> dict[str, str]:
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_DATE": date,
    }


def _git_repo_root(tmp_path: Path) -> tuple[Path, tuple[str, str]]:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text(
        "class RuntimeGraph:\n"
        "    pass\n\n"
        "def build_runtime_graph():\n"
        "    return RuntimeGraph()\n",
        encoding="utf-8",
    )
    _git(root.parent, "init", str(root))
    _git(root, "config", "user.name", "Fixture User")
    _git(root, "config", "user.email", "fixture@example.com")
    _git(root, "add", ".")
    _git(
        root,
        "commit",
        "-m",
        "initial runtime graph",
        env=_commit_env(
            name="Alice Example",
            email="alice@example.com",
            date="2026-06-10T10:00:00-0700",
        ),
    )
    first_hash = _git(root, "rev-parse", "HEAD")
    (root / "src" / "helper.py").write_text(
        "def helper_value() -> bool:\n    return True\n",
        encoding="utf-8",
    )
    (root / "src" / "app.py").write_text(
        "from helper import helper_value\n\n"
        "class RuntimeGraph:\n"
        "    pass\n\n"
        "def build_runtime_graph():\n"
        "    return helper_value() and isinstance(RuntimeGraph(), RuntimeGraph)\n",
        encoding="utf-8",
    )
    _git(root, "add", ".")
    _git(
        root,
        "commit",
        "-m",
        "wire helper into runtime graph",
        env=_commit_env(
            name="Bob Example",
            email="bob@example.com",
            date="2026-06-11T12:30:00+0200",
        ),
    )
    second_hash = _git(root, "rev-parse", "HEAD")
    return root, (first_hash, second_hash)


def _runtime_graph_symbol(snapshot) -> GraphNode:
    return next(node for node in snapshot.nodes if node.label == "RuntimeGraph")


def test_git_overlay_queries_reports_and_service_metadata(tmp_path: Path) -> None:
    root, (first_hash, second_hash) = _git_repo_root(tmp_path)

    snapshot = index_path(root, namespace="fixture")
    commit_nodes = [node for node in snapshot.nodes if node.kind == "git_commit"]
    changed_path_nodes = [
        node for node in snapshot.nodes if node.kind == "git_changed_path"
    ]

    assert snapshot.stats["git_overlay_enabled"] is True
    assert snapshot.stats["git_identity_mode"] == "name_email_hash"
    assert snapshot.stats["git_commit_count"] == 2
    assert snapshot.stats["git_changed_path_count"] >= 2
    assert len(commit_nodes) == 2
    assert {node.source_ref.path for node in changed_path_nodes} >= {
        "src/app.py",
        "src/helper.py",
    }
    assert all("author_email" not in node.metadata for node in commit_nodes)
    assert any(
        node.metadata.get("author_email_hash")
        == hashlib.sha256("alice@example.com".encode("utf-8")).hexdigest()
        for node in commit_nodes
    )

    commits_for_path = recent_commits_for_path(snapshot, "src/app.py", max_results=5)
    assert [hit.node.metadata["commit_hash"] for hit in commits_for_path.hits] == [
        second_hash,
        first_hash,
    ]

    touched_files = files_touched_by_commit(snapshot, second_hash[:12], max_results=10)
    assert {hit.node.source_ref.path for hit in touched_files.hits} == {
        "src/app.py",
        "src/helper.py",
    }

    symbol_commits = commits_touching_symbol_file(
        snapshot,
        _runtime_graph_symbol(snapshot).id,
        max_results=5,
    )
    assert [hit.node.metadata["commit_hash"] for hit in symbol_commits.hits] == [
        second_hash,
        first_hash,
    ]

    report = build_report(snapshot, top_n=5)
    markdown = render_markdown_report(report)
    assert report.summary.git_commit_count == 2
    assert report.summary.git_identity_mode == "name_email_hash"
    assert report.git_commits[0].commit_hash == second_hash
    assert "## Git Overlay" in markdown
    assert "wire helper into runtime graph" in markdown

    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, snapshot_path)
    service = LocalQueryService.from_snapshot_path(snapshot_path)
    capabilities = service.capabilities().to_dict()
    health_response = service.handle_request(
        ServiceRequest(id="health", method="health", params={})
    )[0].to_dict()

    assert capabilities["git_overlay_supported"] is True
    assert capabilities["git_identity_mode"] == "name_email_hash"
    assert capabilities["git_commit_count"] == 2
    assert health_response["result"]["service"]["git_overlay"]["commit_count"] == 2


def test_git_identity_mode_full_is_opt_in(tmp_path: Path) -> None:
    root, _hashes = _git_repo_root(tmp_path)

    snapshot = index_path(root, namespace="fixture", git_identity_mode="full")
    commit_node = next(node for node in snapshot.nodes if node.kind == "git_commit")

    assert snapshot.stats["git_identity_mode"] == "full"
    assert commit_node.metadata["author_email"] in {
        "alice@example.com",
        "bob@example.com",
    }


def test_git_output_is_timezone_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, _hashes = _git_repo_root(tmp_path)

    monkeypatch.setenv("TZ", "UTC")
    if hasattr(time, "tzset"):
        time.tzset()
    utc_snapshot = index_path(root, namespace="fixture")

    monkeypatch.setenv("TZ", "America/Los_Angeles")
    if hasattr(time, "tzset"):
        time.tzset()
    la_snapshot = index_path(root, namespace="fixture")

    assert stable_dumps(utc_snapshot) == stable_dumps(la_snapshot)


def test_non_git_root_and_git_unavailable_surface_typed_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    (root / "README.md").write_text("# Plain\n", encoding="utf-8")

    snapshot = index_path(root, namespace="plain")
    assert "git_not_repo" in {item.reason for item in snapshot.omitted}

    def _missing_git(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("git missing")

    monkeypatch.setattr("pragmagraph.adapters.git_history.subprocess.run", _missing_git)
    unavailable = index_path(root, namespace="plain")
    assert "git_unavailable" in {item.reason for item in unavailable.omitted}


def test_cli_git_commands_emit_json(tmp_path: Path) -> None:
    root, (_first_hash, second_hash) = _git_repo_root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    save_snapshot(index_path(root, namespace="fixture"), snapshot_path)

    commits_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "git-commits-for-path",
                str(snapshot_path),
                "src/app.py",
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    files_payload = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "git-files-for-commit",
                str(snapshot_path),
                second_hash[:12],
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    assert commits_payload["hits"][0]["node"]["metadata"]["commit_hash"] == second_hash
    assert {hit["node"]["source_ref"]["path"] for hit in files_payload["hits"]} == {
        "src/app.py",
        "src/helper.py",
    }
