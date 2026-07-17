from __future__ import annotations

from pathlib import Path

import pytest

from pragmagraph.interchange import (
    FRESHNESS_MATCH,
    FRESHNESS_MISMATCH,
    FRESHNESS_UNKNOWN,
    evaluate_scip_freshness,
    load_native_scip,
)
from pragmagraph.models import PragmaGraphError
from .scip_fixtures import TYPESCRIPT_SCIP


def test_scip_freshness_exact_match_and_unknown_states(tmp_path: Path) -> None:
    root_uri = tmp_path.resolve().as_uri()

    exact = evaluate_scip_freshness(
        index_root=root_uri,
        workspace_root=str(tmp_path),
        index_commit="abc123",
        workspace_commit="abc123",
    )
    unknown = evaluate_scip_freshness()

    assert exact.state == FRESHNESS_MATCH
    assert exact.root_state == FRESHNESS_MATCH
    assert exact.commit_state == FRESHNESS_MATCH
    assert unknown.state == FRESHNESS_UNKNOWN


def test_scip_freshness_permissive_mismatch_is_recorded() -> None:
    result = load_native_scip(
        TYPESCRIPT_SCIP,
        index_commit="old",
        workspace_commit="new",
    )

    assert result.report.freshness.state == FRESHNESS_MISMATCH
    assert result.snapshot.stats["precise_ingestion"]["freshness"]["state"] == (
        FRESHNESS_MISMATCH
    )


def test_scip_freshness_strict_mismatch_rejects_before_output(tmp_path: Path) -> None:
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(PragmaGraphError) as exc_info:
        result = load_native_scip(
            TYPESCRIPT_SCIP,
            index_commit="old",
            workspace_commit="new",
            strict_freshness=True,
        )
        output.write_text(str(result), encoding="utf-8")

    assert exc_info.value.code == "SCIP_FRESHNESS_MISMATCH"
    assert not output.exists()
