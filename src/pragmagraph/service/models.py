"""Transport-neutral DTOs for the PragmaGraph local service surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from pragmagraph.models import PragmaGraphError


def _frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def _tuple_str(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        text = str(value).strip()
        return (text,) if text else ()
    return tuple(str(item) for item in value)  # type: ignore[arg-type]


@dataclass(frozen=True)
class ServiceError:
    """Typed error envelope for the local service surface."""

    code: str
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", str(self.code))
        object.__setattr__(self, "message", str(self.message))
        object.__setattr__(self, "details", _frozen_mapping(self.details))

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
        object.__setattr__(self, "params", _frozen_mapping(self.params))

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
    export_formats: tuple[str, ...] = ()
    report_formats: tuple[str, ...] = ()
    snapshot_id: str = ""
    root_path: str = ""
    snapshot_path: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "supported_methods",
            tuple(sorted(_tuple_str(self.supported_methods))),
        )
        object.__setattr__(
            self, "parser_set", tuple(sorted(_tuple_str(self.parser_set)))
        )
        object.__setattr__(
            self, "export_formats", tuple(sorted(_tuple_str(self.export_formats)))
        )
        object.__setattr__(
            self, "report_formats", tuple(sorted(_tuple_str(self.report_formats)))
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
            "export_formats": list(self.export_formats),
            "report_formats": list(self.report_formats),
            "snapshot_id": self.snapshot_id,
            "root_path": self.root_path,
            "snapshot_path": self.snapshot_path,
        }


__all__ = [
    "ServiceCapabilities",
    "ServiceError",
    "ServiceRequest",
    "ServiceResponse",
]
