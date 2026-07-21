"""Transport-neutral DTOs for the PragmaGraph local service surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pragmagraph._immutables import frozen_mapping, tuple_str
from pragmagraph.models import PragmaGraphError


@dataclass(frozen=True)
class ServiceError:
    """Typed error envelope for the local service surface."""

    code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", str(self.code))
        object.__setattr__(self, "message", str(self.message))
        object.__setattr__(self, "details", frozen_mapping(self.details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ServiceRequest:
    """One local service request."""

    id: str
    method: str
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", str(self.id or ""))
        object.__setattr__(self, "method", str(self.method or ""))
        object.__setattr__(self, "params", frozen_mapping(self.params))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ServiceRequest":
        method = payload.get("method")
        if not isinstance(method, str) or not method.strip():
            raise PragmaGraphError(
                "service request must include a non-empty string method",
                code="invalid_request",
            )
        params = payload.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, Mapping):
            raise PragmaGraphError(
                "service request params must be an object",
                code="invalid_request",
                details={"method": method},
            )
        return cls(
            id=str(payload.get("id", "") or ""),
            method=method.strip(),
            params=dict(params),
        )


@dataclass(frozen=True)
class ServiceResponse:
    """Typed service response envelope."""

    id: str
    ok: bool
    result: Any = None
    error: ServiceError | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", str(self.id or ""))

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.id, "ok": self.ok}
        if self.ok:
            payload["result"] = self.result
        elif self.error is not None:
            payload["error"] = self.error.to_dict()
        return payload

    @classmethod
    def success(cls, request_id: str, result: Any) -> "ServiceResponse":
        return cls(id=request_id, ok=True, result=result)

    @classmethod
    def failure(
        cls,
        request_id: str,
        *,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> "ServiceResponse":
        return cls(
            id=request_id,
            ok=False,
            error=ServiceError(code=code, message=message, details=details or {}),
        )


@dataclass(frozen=True)
class ServiceCapabilities:
    """Advertised capabilities for one live service instance."""

    service_version: str
    package_version: str
    package_status: str
    startup_mode: str
    namespace: str
    refresh_supported: bool
    supported_methods: tuple[str, ...] = ()
    snapshot_schema_version: str = ""
    indexer_version: str = ""
    graphify_format: str = ""
    export_schema_version: str = ""
    manifest_schema_version: str = ""
    parser_set: tuple[str, ...] = ()
    parser_versions: tuple[str, ...] = ()
    export_formats: tuple[str, ...] = ()
    export_profiles: tuple[str, ...] = ()
    query_pagination_supported: bool = True
    report_formats: tuple[str, ...] = ()
    snapshot_id: str = ""
    root_path: str = ""
    snapshot_path: str = ""
    workspace_path: str = ""
    git_overlay_supported: bool = False
    git_identity_mode: str = ""
    git_commit_count: int = 0
    git_changed_path_count: int = 0
    store_backend: str = ""
    store_path: str = ""
    store_manifest_schema_version: str = ""
    store_fts_available: bool = False
    native_scip_available: bool = False
    precise_ingestion_loaded: bool = False
    precise_producer: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "supported_methods",
            tuple(sorted(tuple_str(self.supported_methods))),
        )
        object.__setattr__(
            self, "parser_set", tuple(sorted(tuple_str(self.parser_set)))
        )
        object.__setattr__(
            self, "parser_versions", tuple(sorted(tuple_str(self.parser_versions)))
        )
        object.__setattr__(
            self, "export_formats", tuple(sorted(tuple_str(self.export_formats)))
        )
        object.__setattr__(
            self, "export_profiles", tuple(sorted(tuple_str(self.export_profiles)))
        )
        object.__setattr__(
            self, "report_formats", tuple(sorted(tuple_str(self.report_formats)))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_version": self.service_version,
            "package_version": self.package_version,
            "package_status": self.package_status,
            "startup_mode": self.startup_mode,
            "namespace": self.namespace,
            "refresh_supported": self.refresh_supported,
            "supported_methods": list(self.supported_methods),
            "snapshot_schema_version": self.snapshot_schema_version,
            "indexer_version": self.indexer_version,
            "graphify_format": self.graphify_format,
            "export_schema_version": self.export_schema_version,
            "manifest_schema_version": self.manifest_schema_version,
            "parser_set": list(self.parser_set),
            "parser_versions": list(self.parser_versions),
            "export_formats": list(self.export_formats),
            "export_profiles": list(self.export_profiles),
            "query_pagination_supported": self.query_pagination_supported,
            "report_formats": list(self.report_formats),
            "snapshot_id": self.snapshot_id,
            "root_path": self.root_path,
            "snapshot_path": self.snapshot_path,
            "workspace_path": self.workspace_path,
            "git_overlay_supported": self.git_overlay_supported,
            "git_identity_mode": self.git_identity_mode,
            "git_commit_count": self.git_commit_count,
            "git_changed_path_count": self.git_changed_path_count,
            "store_backend": self.store_backend,
            "store_path": self.store_path,
            "store_manifest_schema_version": self.store_manifest_schema_version,
            "store_fts_available": self.store_fts_available,
            "native_scip_available": self.native_scip_available,
            "precise_ingestion_loaded": self.precise_ingestion_loaded,
            "precise_producer": self.precise_producer,
        }


@dataclass(frozen=True)
class ServiceStatus:
    """Machine-readable readiness facts for one live service instance."""

    service_version: str
    startup_mode: str
    namespace: str
    refresh_supported: bool
    snapshot_id: str
    graph: Mapping[str, Any] = field(default_factory=dict)
    refresh_readiness: Mapping[str, Any] = field(default_factory=dict)
    artifact_presence: Mapping[str, Any] = field(default_factory=dict)
    last_refresh: Mapping[str, Any] | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    root_path: str = ""
    snapshot_path: str = ""
    workspace_path: str = ""
    store_path: str = ""
    manifest_schema_version: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "graph", frozen_mapping(self.graph))
        object.__setattr__(
            self,
            "refresh_readiness",
            frozen_mapping(self.refresh_readiness),
        )
        object.__setattr__(
            self,
            "artifact_presence",
            frozen_mapping(self.artifact_presence),
        )
        if self.last_refresh is not None:
            object.__setattr__(self, "last_refresh", frozen_mapping(self.last_refresh))
        object.__setattr__(self, "diagnostics", frozen_mapping(self.diagnostics))

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_version": self.service_version,
            "startup_mode": self.startup_mode,
            "namespace": self.namespace,
            "refresh_supported": self.refresh_supported,
            "snapshot_id": self.snapshot_id,
            "root_path": self.root_path,
            "snapshot_path": self.snapshot_path,
            "workspace_path": self.workspace_path,
            "store_path": self.store_path,
            "manifest_schema_version": self.manifest_schema_version,
            "graph": dict(self.graph),
            "refresh_readiness": dict(self.refresh_readiness),
            "artifact_presence": dict(self.artifact_presence),
            "last_refresh": (
                dict(self.last_refresh) if self.last_refresh is not None else None
            ),
            "diagnostics": dict(self.diagnostics),
        }


__all__ = [
    "ServiceCapabilities",
    "ServiceError",
    "ServiceRequest",
    "ServiceResponse",
    "ServiceStatus",
]
