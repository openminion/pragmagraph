from __future__ import annotations

import json
from pathlib import Path

import pytest

from pragmagraph.__main__ import main
from pragmagraph.interchange import ObservedSymbolFact, snapshot_from_compiler_facts
from pragmagraph.models import PragmaGraphError
from pragmagraph.storage import load_snapshot, save_snapshot
from .scip_fixtures import TYPESCRIPT_SCIP


def test_precise_import_cli_writes_native_snapshot(tmp_path: Path, capsys) -> None:
    output = tmp_path / "precise.json"

    exit_code = main(
        [
            "precise-import",
            str(TYPESCRIPT_SCIP),
            "--out",
            str(output),
            "--namespace",
            "fixture",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["merged"] is False
    assert payload["report"]["producer"]["name"] == "scip-typescript"
    assert load_snapshot(output).stats["precise_ingestion"]["format"] == (
        "scip.protobuf.v1"
    )


def test_precise_import_cli_merges_with_base_snapshot(tmp_path: Path, capsys) -> None:
    base_path = tmp_path / "base.json"
    output = tmp_path / "merged.json"
    base = snapshot_from_compiler_facts(
        (
            ObservedSymbolFact(
                symbol="local README#overview.",
                label="overview",
                path="README.md",
                kind="document_symbol",
            ),
        ),
        namespace="fixture",
        producer="local",
    )
    save_snapshot(base, base_path)

    main(
        [
            "precise-import",
            str(TYPESCRIPT_SCIP),
            "--base",
            str(base_path),
            "--out",
            str(output),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    merged = load_snapshot(output)

    assert payload["merged"] is True
    assert any(node.label == "overview" for node in merged.nodes)
    assert any(node.metadata.get("scip_symbol") for node in merged.nodes)


def test_precise_import_cli_strict_failure_is_atomic(tmp_path: Path) -> None:
    output = tmp_path / "must-not-exist.json"

    with pytest.raises(PragmaGraphError) as exc_info:
        main(
            [
                "precise-import",
                str(TYPESCRIPT_SCIP),
                "--out",
                str(output),
                "--index-commit",
                "old",
                "--workspace-commit",
                "new",
                "--strict-freshness",
            ]
        )

    assert exc_info.value.code == "SCIP_FRESHNESS_MISMATCH"
    assert not output.exists()
