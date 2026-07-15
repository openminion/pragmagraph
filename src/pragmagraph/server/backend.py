"""Backend bridge wiring MCP tool calls onto public `pragmagraph.service` APIs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pragmagraph import __version__
from pragmagraph.adapters import DEFAULT_GIT_IDENTITY_MODE
from pragmagraph.service import (
    ERROR_INVALID_PARAMS,
    ERROR_INVALID_REQUEST,
    ERROR_REFRESH_UNSUPPORTED,
    METHOD_CAPABILITIES,
    METHOD_EXPLAIN,
    METHOD_EXPORT,
    METHOD_GRAPHIFY_EXPORT,
    METHOD_HEALTH,
    METHOD_NEIGHBORHOOD,
    METHOD_PATH,
    METHOD_QUERY,
    METHOD_REFRESH,
    METHOD_REPORT,
    LocalQueryService,
    ServiceRequest,
)

from pragmagraph.server.contracts import (
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    PragmaGraphServerError,
    ServiceInvocationError,
    UnsupportedCapabilityError,
)
from pragmagraph.server.service_core import assert_request_keys_subset
from pragmagraph.server.resources import ResourceRegistry
from pragmagraph.server.tools import ToolHandler, ToolRegistry


@dataclass(frozen=True)
class ServiceConfig:
    """Operator config for one loaded MCP service instance."""

    snapshot_path: str | None = None
    root_path: str | None = None
    namespace: str = "default"
    manifest_in: str | None = None
    snapshot_out: str | None = None
    manifest_out: str | None = None
    state_out: str | None = None
    cache_path: str | None = None
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE

    def __post_init__(self) -> None:
        has_snapshot = bool(str(self.snapshot_path or "").strip())
        has_root = bool(str(self.root_path or "").strip())
        if has_snapshot == has_root:
            raise PragmaGraphServerError(
                "exactly one of snapshot_path or root_path is required",
                code=JSONRPC_INVALID_PARAMS,
                details={
                    "snapshot_path": self.snapshot_path or "",
                    "root_path": self.root_path or "",
                },
            )


_SERVICE_TOOL_BINDINGS = {
    "pragmagraph_health": (METHOD_HEALTH, "health"),
    "pragmagraph_query": (METHOD_QUERY, "query_result"),
    "pragmagraph_explain": (METHOD_EXPLAIN, "query_result"),
    "pragmagraph_neighborhood": (METHOD_NEIGHBORHOOD, "neighborhood"),
    "pragmagraph_path": (METHOD_PATH, "path"),
    "pragmagraph_report": (METHOD_REPORT, "report"),
    "pragmagraph_export": (METHOD_EXPORT, "export"),
    "pragmagraph_graphify_export": (METHOD_GRAPHIFY_EXPORT, "graphify_export"),
    "pragmagraph_refresh": (METHOD_REFRESH, "refresh"),
}


def _service_from_config(config: ServiceConfig) -> LocalQueryService:
    if config.snapshot_path:
        return LocalQueryService.from_snapshot_path(config.snapshot_path)
    return LocalQueryService.from_root(
        Path(str(config.root_path)),
        namespace=config.namespace,
        manifest_path=config.manifest_in,
        snapshot_out_path=config.snapshot_out,
        manifest_out_path=config.manifest_out,
        state_out_path=config.state_out,
        cache_path=config.cache_path,
        git_identity_mode=config.git_identity_mode,
    )


def _invoke_service(
    service: LocalQueryService,
    *,
    tool_name: str,
    method: str,
    params: Mapping[str, Any],
) -> Mapping[str, Any]:
    response, _ = service.handle_request(
        ServiceRequest(id=tool_name, method=method, params=params)
    )
    payload = response.to_dict()
    if response.ok:
        result = payload.get("result")
        return result if isinstance(result, Mapping) else {}
    error = payload.get("error")
    if not isinstance(error, Mapping):
        raise ServiceInvocationError(
            tool_name,
            service_code="internal_service_error",
            service_message="service returned malformed error payload",
        )
    service_code = str(error.get("code") or "")
    service_message = str(error.get("message") or "service call failed")
    service_details = error.get("details")
    typed_details = (
        dict(service_details) if isinstance(service_details, Mapping) else {}
    )
    if service_code == ERROR_REFRESH_UNSUPPORTED:
        raise UnsupportedCapabilityError(
            tool_name,
            capability="refresh",
            details={
                "service_error_code": service_code,
                "service_details": typed_details,
            },
        )
    if service_code == ERROR_INVALID_PARAMS:
        raise PragmaGraphServerError(
            service_message,
            code=JSONRPC_INVALID_PARAMS,
            details={
                "tool_name": tool_name,
                "service_error_code": service_code,
                "service_details": typed_details,
            },
        )
    if service_code == ERROR_INVALID_REQUEST:
        raise PragmaGraphServerError(
            service_message,
            code=JSONRPC_INVALID_REQUEST,
            details={
                "tool_name": tool_name,
                "service_error_code": service_code,
                "service_details": typed_details,
            },
        )
    raise ServiceInvocationError(
        tool_name,
        service_code=service_code,
        service_message=service_message,
        service_details=typed_details,
    )


def _wired_capabilities_handler(service: LocalQueryService) -> ToolHandler:
    def _handler(**kwargs: Any) -> Mapping[str, Any]:
        assert_request_keys_subset("pragmagraph_capabilities", set(kwargs.keys()))
        return {
            "protocol_version": "2025-06-18",
            "server_name": "pragmagraph-server",
            "server_version": __version__,
            "service": _invoke_service(
                service,
                tool_name="pragmagraph_capabilities",
                method=METHOD_CAPABILITIES,
                params={},
            ),
            "supported_tools": list(ToolRegistry.default().names()),
        }

    return _handler


def _service_tool_handler(
    service: LocalQueryService,
    *,
    tool_name: str,
    method: str,
    result_key: str,
) -> ToolHandler:
    def _handler(**kwargs: Any) -> Mapping[str, Any]:
        assert_request_keys_subset(tool_name, set(kwargs.keys()))
        result = _invoke_service(
            service, tool_name=tool_name, method=method, params=kwargs
        )
        return {result_key: result}

    return _handler


def build_wired_registry(config: ServiceConfig) -> ToolRegistry:
    """Construct a ToolRegistry wired to one live `LocalQueryService`."""

    service = _service_from_config(config)
    registry = ToolRegistry.default()
    registry.resources = ResourceRegistry(service)
    registry._handlers = {}

    for schema in registry.schemas():
        if schema.name == "pragmagraph_capabilities":
            handler = _wired_capabilities_handler(service)
        else:
            try:
                method, result_key = _SERVICE_TOOL_BINDINGS[schema.name]
            except KeyError as exc:  # pragma: no cover - closed schema set
                raise RuntimeError(
                    f"missing service binding for {schema.name}"
                ) from exc
            handler = _service_tool_handler(
                service,
                tool_name=schema.name,
                method=method,
                result_key=result_key,
            )
        registry.register(schema, handler)
    return registry


__all__ = ["ServiceConfig", "build_wired_registry"]
