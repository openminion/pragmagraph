from __future__ import annotations

import hashlib

import pytest

from pragmagraph.interchange import load_native_scip
from pragmagraph.storage import stable_dumps
from .scip_fixtures import PYTHON_SCIP, TYPESCRIPT_SCIP


@pytest.mark.parametrize(
    (
        "path",
        "producer",
        "version",
        "sha256",
        "expected_root",
        "expected_paths",
    ),
    (
        (
            PYTHON_SCIP,
            "scip-python",
            "0.6.6",
            "28bcb9178650c4918cb594fb11f8a06daceb75d5803262def9ee09ba623b9e04",
            "file:///fixtures/pragmagraph/scip/python",
            {"demo/client.py", "demo/service.py"},
        ),
        (
            TYPESCRIPT_SCIP,
            "scip-typescript",
            "0.4.0",
            "0a4c2fc9cb0355d089db2d0f7c762b9269809765c960c63d4f1cf3edf0460ca9",
            "file:///fixtures/pragmagraph/scip/typescript",
            {"src/client.ts", "src/service.ts"},
        ),
    ),
)
def test_official_producer_fixture_is_exact_and_deterministic(
    path,
    producer: str,
    version: str,
    sha256: str,
    expected_root: str,
    expected_paths: set[str],
) -> None:
    assert hashlib.sha256(path.read_bytes()).hexdigest() == sha256

    first = load_native_scip(path, namespace="certified")
    second = load_native_scip(path, namespace="certified")
    symbol_paths = {
        node.source_ref.path
        for node in first.snapshot.nodes
        if node.kind == "symbol" and node.source_ref.path
    }
    reference_paths = {
        edge.source_ref.path for edge in first.snapshot.edges if edge.kind == "mentions"
    }

    assert first.report.producer.to_dict() == {"name": producer, "version": version}
    assert first.report.project_root == expected_root
    assert first.report.document_count == 2
    assert first.report.symbol_count >= 4
    assert first.report.reference_count >= 3
    assert expected_paths <= symbol_paths
    assert reference_paths
    assert stable_dumps(first.snapshot) == stable_dumps(second.snapshot)
