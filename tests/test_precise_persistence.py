from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from pragmagraph.export import project_snapshot
from pragmagraph.interchange import load_native_scip
from pragmagraph.refresh import build_ci_delta
from pragmagraph.storage import (
    SQLiteGraphStore,
    load_snapshot,
    save_snapshot,
    stable_dumps,
)
from .scip_fixtures import TYPESCRIPT_SCIP


def _precise_snapshot(tmp_path: Path):
    return load_native_scip(
        TYPESCRIPT_SCIP,
        namespace="persistent",
        root_path=str(tmp_path),
        index_commit="abc123",
        workspace_commit="abc123",
    ).snapshot


def test_precise_report_round_trips_through_json_and_sqlite(tmp_path: Path) -> None:
    snapshot = _precise_snapshot(tmp_path)
    json_path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, json_path)

    json_restored = load_snapshot(json_path)
    sqlite_restored = SQLiteGraphStore.from_snapshot(
        snapshot,
        tmp_path / "graph.sqlite",
    ).export_snapshot()

    assert stable_dumps(json_restored) == stable_dumps(snapshot)
    assert stable_dumps(sqlite_restored) == stable_dumps(snapshot)
    assert sqlite_restored.stats["precise_ingestion"]["producer"]["name"] == (
        "scip-typescript"
    )


def test_portable_export_redacts_precise_machine_roots_without_mutation(
    tmp_path: Path,
) -> None:
    snapshot = _precise_snapshot(tmp_path)

    projection = project_snapshot(snapshot, profile="portable")
    report = projection.snapshot.stats["precise_ingestion"]

    assert report["project_root"] == ""
    assert report["freshness"]["index_root"] == ""
    assert report["freshness"]["workspace_root"] == ""
    assert "stats.precise_ingestion.project_root" in projection.redacted_fields
    assert snapshot.stats["precise_ingestion"]["project_root"].startswith("file://")


def test_precise_report_changes_are_visible_in_ci_delta(tmp_path: Path) -> None:
    before = _precise_snapshot(tmp_path)
    report = dict(before.stats["precise_ingestion"])
    report["producer"] = {"name": "scip-typescript", "version": "next"}
    after = replace(before, stats={**dict(before.stats), "precise_ingestion": report})

    delta = build_ci_delta(before, after)

    assert delta.has_changes is True
    assert delta.changed_snapshot_fields == ("stats",)
    assert delta.to_dict()["changed_snapshot_fields"] == ["stats"]
