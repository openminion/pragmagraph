from __future__ import annotations

import importlib

import pytest

from pragmagraph.interchange import (
    ACCEPTED_SCIP_FIELDS,
    SCIP_NATIVE_FORMAT,
    ScipFreshness,
    ScipIngestionReport,
    ScipLossReport,
    ScipProducer,
    native_scip_available,
)
from pragmagraph.interchange import native as native_module
from pragmagraph.models import PragmaGraphError


def test_native_scip_contracts_are_immutable_and_serializable() -> None:
    report = ScipIngestionReport(
        producer=ScipProducer(name="fixture", version="1.0"),
        languages=("typescript", "python", "python"),
        freshness=ScipFreshness(),
        loss=ScipLossReport(omitted_counts={"documentation": 2}),
    )

    assert report.format == SCIP_NATIVE_FORMAT
    assert report.languages == ("python", "python", "typescript")
    assert report.to_dict()["loss"]["omitted_counts"] == {"documentation": 2}
    assert "documents.occurrences.symbol" in ACCEPTED_SCIP_FIELDS


def test_native_support_is_available_with_the_optional_extra() -> None:
    assert native_scip_available() is True


def test_native_support_is_unavailable_without_parent_namespace(monkeypatch) -> None:
    def fail_parent_lookup(name: str):
        if name == "google.protobuf":
            raise ModuleNotFoundError("google")
        return object()

    monkeypatch.setattr(native_module.importlib.util, "find_spec", fail_parent_lookup)

    assert native_scip_available() is False


def test_missing_protobuf_dependency_returns_typed_error(monkeypatch) -> None:
    real_import = importlib.import_module

    def fail_schema_import(name: str):
        if name.endswith("scip_pb2"):
            raise ModuleNotFoundError("google.protobuf")
        return real_import(name)

    monkeypatch.setattr(native_module.importlib, "import_module", fail_schema_import)

    with pytest.raises(PragmaGraphError) as exc_info:
        native_module.snapshot_from_scip_protobuf(b"")

    assert exc_info.value.code == "SCIP_SUPPORT_UNAVAILABLE"
    assert exc_info.value.details["install"] == "pragmagraph[scip]"
