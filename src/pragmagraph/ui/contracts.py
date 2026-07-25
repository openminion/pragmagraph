"""Package-owned UI boundary contracts for the PragmaGraph workbench."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

UiTransportKind = Literal["openminion_workbench"]
UiTransportStatus = Literal["planned_not_implemented"]
UiScreenId = Literal[
    "search",
    "result_detail",
    "neighborhood",
    "path",
    "provider_status",
    "project_health",
    "evidence",
    "delta_review",
]


@dataclass(frozen=True, slots=True)
class UiTransportBoundary:
    """Typed statement of the current UI/runtime split for PragmaGraph."""

    owner_import_root: str
    runtime_package: str
    transport: UiTransportKind
    transport_status: UiTransportStatus
    ui_owner_surface: str
    api_surface: str
    imports_openminion: bool
    imports_runtime_package: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class UiScreenDefinition:
    """One first-pass screen in the third-brain workbench."""

    screen_id: UiScreenId
    route: str
    title: str
    primary_payloads: tuple[str, ...]
    mvp: bool = False
    mutating: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_default_ui_boundary() -> UiTransportBoundary:
    """Return the canonical package-to-workbench boundary for PragmaGraph."""
    return UiTransportBoundary(
        owner_import_root="pragmagraph.ui",
        runtime_package="openminion",
        transport="openminion_workbench",
        transport_status="planned_not_implemented",
        ui_owner_surface="openminion third-brain workbench",
        api_surface="openminion third-brain adapter layer",
        imports_openminion=False,
        imports_runtime_package=False,
    )


def build_ui_screen_manifest() -> tuple[UiScreenDefinition, ...]:
    """Return the first-pass route manifest for the observed-fact workbench."""
    return (
        UiScreenDefinition(
            screen_id="search",
            route="/third-brain/search",
            title="Third-Brain Search",
            primary_payloads=(
                "GraphQueryRequest",
                "GraphQueryResult",
                "KnowledgeGraphCapabilities",
            ),
            mvp=True,
        ),
        UiScreenDefinition(
            screen_id="result_detail",
            route="/third-brain/result/:result_id",
            title="Result Detail",
            primary_payloads=(
                "GraphContextItem",
                "GraphSourceRef",
                "GraphOmittedItem",
            ),
            mvp=True,
        ),
        UiScreenDefinition(
            screen_id="neighborhood",
            route="/third-brain/neighborhood/:entity_id",
            title="Neighborhood",
            primary_payloads=("GraphNeighborhoodRequest", "GraphQueryResult"),
            mvp=True,
        ),
        UiScreenDefinition(
            screen_id="path",
            route="/third-brain/path",
            title="Path Explorer",
            primary_payloads=("GraphPathRequest", "GraphPathResult"),
            mvp=True,
        ),
        UiScreenDefinition(
            screen_id="provider_status",
            route="/third-brain/providers",
            title="Provider Status",
            primary_payloads=(
                "KnowledgeGraphHealth",
                "KnowledgeGraphCapabilities",
                "GraphRefreshResult",
            ),
            mvp=True,
            mutating=True,
        ),
        UiScreenDefinition(
            screen_id="project_health",
            route="/third-brain/project-health",
            title="Project Health",
            primary_payloads=(
                "KnowledgeGraphHealth",
                "GraphRefreshResult",
                "GraphOmittedItem",
                "ParserDiagnostic",
            ),
            mvp=True,
        ),
        UiScreenDefinition(
            screen_id="evidence",
            route="/third-brain/evidence",
            title="Evidence Workbench",
            primary_payloads=(
                "ServiceStatus",
                "StoreSearchExplanation",
                "StoreRoundTripReport",
                "AgentContext",
            ),
            mvp=True,
        ),
        UiScreenDefinition(
            screen_id="delta_review",
            route="/third-brain/delta-review",
            title="Delta Review",
            primary_payloads=(
                "CiDeltaReport",
                "RefreshStatus",
                "SnapshotStructuralDelta",
            ),
            mvp=True,
        ),
    )
