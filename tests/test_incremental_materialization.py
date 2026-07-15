from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from pragmagraph.incremental import load_extraction_cache, save_extraction_cache
from pragmagraph.models import PragmaGraphError, QueryRequest
from pragmagraph.operations import build_refresh_profile, run_refresh_profile
from pragmagraph.refresh import refresh_snapshot, refresh_snapshot_incremental
from pragmagraph.storage import (
    JsonSnapshotStore,
    SQLiteGraphStore,
    save_snapshot,
    stable_dumps,
)


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "src" / "app.py").write_text(
        "from helper import value\n\ndef run():\n    return value()\n",
        encoding="utf-8",
    )
    (root / "src" / "helper.py").write_text(
        "def value():\n    return 1\n", encoding="utf-8"
    )
    (root / "docs" / "guide.md").write_text(
        "# Guide\n\nUse `src/app.py`.\n", encoding="utf-8"
    )
    return root


def test_incremental_refresh_reuses_unchanged_fragments_and_matches_full(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    first, cache = refresh_snapshot_incremental(root)
    second, next_cache = refresh_snapshot_incremental(
        root,
        previous_manifest=first.manifest,
        previous_snapshot=first.snapshot,
        previous_cache=cache,
    )
    full = refresh_snapshot(root)

    assert stable_dumps(second.snapshot) == stable_dumps(full.snapshot)
    assert second.work.parsed_path_count == 0
    assert second.work.reused_path_count == len(second.manifest.entries)
    assert second.work.resolution_overlay_rebuilt is True
    assert second.work.git_overlay_rebuilt is False
    assert next_cache.to_dict() == cache.to_dict()


def test_incremental_refresh_parses_only_changed_file(tmp_path: Path) -> None:
    root = _root(tmp_path)
    first, cache = refresh_snapshot_incremental(root)
    (root / "src" / "helper.py").write_text(
        "def value():\n    return 2\n", encoding="utf-8"
    )

    changed, _ = refresh_snapshot_incremental(
        root,
        previous_manifest=first.manifest,
        previous_snapshot=first.snapshot,
        previous_cache=cache,
    )

    assert changed.work.parsed_path_count == 1
    assert changed.changed_paths == ("src/helper.py",)
    assert stable_dumps(changed.snapshot) == stable_dumps(
        refresh_snapshot(root).snapshot
    )


def test_profile_rebuilds_and_replaces_corrupt_cache(tmp_path: Path) -> None:
    root = _root(tmp_path)
    cache_path = tmp_path / "state" / "cache.json"
    cache_path.parent.mkdir()
    cache_path.write_text("not json", encoding="utf-8")
    profile = build_refresh_profile(
        label="fixture",
        root_path=root,
        snapshot_path=tmp_path / "state" / "snapshot.json",
        manifest_path=tmp_path / "state" / "manifest.json",
        state_path=tmp_path / "state" / "status.json",
        cache_path=cache_path,
    )

    operation = run_refresh_profile(profile)

    assert operation.result.work.cache_fallback_reason == "invalid_extraction_cache"
    assert load_extraction_cache(cache_path).fragments


def test_cache_serialization_is_deterministic(tmp_path: Path) -> None:
    _, cache = refresh_snapshot_incremental(_root(tmp_path))
    first = save_extraction_cache(cache, tmp_path / "first.json")
    second = save_extraction_cache(cache, tmp_path / "second.json")

    assert first.read_bytes() == second.read_bytes()


def test_sqlite_delta_is_bounded_atomic_and_export_equivalent(tmp_path: Path) -> None:
    root = _root(tmp_path)
    before = refresh_snapshot(root).snapshot
    store = SQLiteGraphStore.from_snapshot(before, tmp_path / "graph.sqlite")
    (root / "src" / "helper.py").write_text(
        "def value():\n    return 9\n", encoding="utf-8"
    )
    after = refresh_snapshot(root).snapshot

    report = store.apply_snapshot_delta(after)

    assert stable_dumps(store.export_snapshot()) == stable_dumps(after)
    assert 0 < report.normalized_rows_written < len(after.nodes) + len(after.edges)
    assert report.snapshot_payload_bytes_written == len(
        stable_dumps(after).encode("utf-8")
    )
    original = stable_dumps(store.export_snapshot())
    with pytest.raises(sqlite3.OperationalError):
        store.apply_snapshot_delta(before, fail_after="snapshot")
    assert stable_dumps(store.export_snapshot()) == original


def test_sqlite_v1_is_readable_then_migrates_idempotently(tmp_path: Path) -> None:
    snapshot = refresh_snapshot(_root(tmp_path)).snapshot
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "graph.sqlite")
    with sqlite3.connect(store.store_path) as connection:
        payload = json.loads(
            connection.execute(
                "SELECT payload FROM store_manifest WHERE id = 'current'"
            ).fetchone()[0]
        )
        payload["schema_version"] = "pragmagraph.sqlite_store.v1alpha1"
        connection.execute(
            "UPDATE store_manifest SET payload = ? WHERE id = 'current'",
            (json.dumps(payload, sort_keys=True),),
        )

    fallback = store.query("run")
    assert fallback.diagnostics["strategy"] == "snapshot_fallback"
    assert fallback.diagnostics["fallback_reason"] == "migration_required"
    with pytest.raises(PragmaGraphError, match="migration is required"):
        store.apply_snapshot_delta(snapshot)
    assert store.migrate().schema_version == "pragmagraph.sqlite_store.v2alpha1"
    assert store.migrate().schema_version == "pragmagraph.sqlite_store.v2alpha1"


@pytest.mark.parametrize(
    "text",
    ["Runtime", "run", "py", "src/helper.py", "", "value"],
)
def test_sqlite_query_matches_json_oracle_without_snapshot_deserialization(
    tmp_path: Path,
    text: str,
) -> None:
    snapshot = refresh_snapshot(_root(tmp_path)).snapshot
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "graph.sqlite")
    request = QueryRequest(query=text, max_results=20)

    actual = store.query(request)
    expected = JsonSnapshotStore(snapshot).query(request)

    assert [hit.to_dict() for hit in actual.hits] == [
        hit.to_dict() for hit in expected.hits
    ]
    assert [item.to_dict() for item in actual.omitted] == [
        item.to_dict() for item in expected.omitted
    ]
    assert actual.diagnostics["snapshot_deserialized"] is False


def test_sqlite_traversal_matches_oracle_and_reports_indexed_strategy(
    tmp_path: Path,
) -> None:
    snapshot = refresh_snapshot(_root(tmp_path)).snapshot
    store = SQLiteGraphStore.from_snapshot(snapshot, tmp_path / "graph.sqlite")
    oracle = JsonSnapshotStore(snapshot)
    source = next(node for node in snapshot.nodes if node.label == "run")

    actual = store.neighborhood(source.id, depth=2, max_results=20)
    expected = oracle.neighborhood(source.id, depth=2, max_results=20)

    assert [hit.node.id for hit in actual.hits] == [
        hit.node.id for hit in expected.hits
    ]
    assert actual.diagnostics["strategy"] == "indexed_traversal"
    assert actual.diagnostics["snapshot_deserialized"] is False


def test_cli_incremental_refresh_and_store_update_surface_work_facts(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    snapshot_path = tmp_path / "snapshot.json"
    manifest_path = tmp_path / "manifest.json"
    cache_path = tmp_path / "cache.json"
    command = [
        sys.executable,
        "-m",
        "pragmagraph",
        "refresh",
        str(root),
        "--out",
        str(snapshot_path),
        "--manifest-out",
        str(manifest_path),
        "--cache-out",
        str(cache_path),
        "--json",
    ]
    first = json.loads(
        subprocess.run(command, check=True, capture_output=True, text=True).stdout
    )
    second = json.loads(
        subprocess.run(
            [
                *command[:-1],
                "--manifest-in",
                str(manifest_path),
                "--cache-in",
                str(cache_path),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    store_path = tmp_path / "graph.sqlite"
    SQLiteGraphStore.from_snapshot(refresh_snapshot(root).snapshot, store_path)
    save_snapshot(refresh_snapshot(root).snapshot, snapshot_path)
    updated = json.loads(
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pragmagraph",
                "store-update",
                str(store_path),
                str(snapshot_path),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )

    assert first["work"]["strategy"] == "incremental"
    assert second["work"]["parsed_path_count"] == 0
    assert updated["strategy"] == "delta"
