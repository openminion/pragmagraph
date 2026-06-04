"""Transport-neutral runtime for the PragmaGraph local service surface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.contracts import INDEXER_VERSION, SCHEMA_VERSION
from pragmagraph.export import render_graph_export
from pragmagraph.graphify import GRAPHIFY_INTEROP_FORMAT, to_graphify_payload
from pragmagraph.models import (
    GraphSnapshot,
    PragmaGraphError,
    QueryRequest,
    RefreshManifest,
)
from pragmagraph.query import health, neighborhood, path, query
from pragmagraph.refresh import load_manifest, refresh_snapshot, save_manifest
from pragmagraph.report import build_report, render_markdown_report
from pragmagraph.service.constants import (
    ERROR_INTERNAL,
    ERROR_INVALID_PARAMS,
    ERROR_NOT_FOUND,
    ERROR_REFRESH_UNSUPPORTED,
    ERROR_UNSUPPORTED_METHOD,
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
    METHOD_SHUTDOWN,
    SERVICE_METHODS,
    SERVICE_VERSION,
    STARTUP_MODE_ROOT,
    STARTUP_MODE_SNAPSHOT,
)
from pragmagraph.service.models import (
    ServiceCapabilities,
    ServiceRequest,
    ServiceResponse,
)
from pragmagraph.storage import load_snapshot, save_snapshot


@dataclass(frozen=True)
class ServiceStartup:
    """Startup configuration for one local service instance."""

    mode: str
    namespace: str
    snapshot_path: str = ""
    root_path: str = ""
    manifest_path: str = ""
    snapshot_out_path: str = ""
    manifest_out_path: str = ""


class LocalQueryService:
    """One long-lived local graph service over a single active snapshot."""

    def __init__(
        self,
        *,
        snapshot: GraphSnapshot,
        startup: ServiceStartup,
        manifest: RefreshManifest | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._startup = startup
        self._manifest = manifest

    @classmethod
    def from_snapshot_path(cls, snapshot_path: str | Path) -> "LocalQueryService":
        snapshot = load_snapshot(snapshot_path)
        return cls(
            snapshot=snapshot,
            startup=ServiceStartup(
                mode=STARTUP_MODE_SNAPSHOT,
                namespace=snapshot.namespace,
                snapshot_path=str(Path(snapshot_path)),
            ),
        )

    @classmethod
    def from_root(
        cls,
        root_path: str | Path,
        *,
        namespace: str = "default",
        manifest_path: str | Path | None = None,
        snapshot_out_path: str | Path | None = None,
        manifest_out_path: str | Path | None = None,
    ) -> "LocalQueryService":
        loaded_manifest = None
        if manifest_path and Path(manifest_path).exists():
            loaded_manifest = load_manifest(manifest_path)
        refresh = refresh_snapshot(
            root_path,
            namespace=namespace,
            previous_manifest=loaded_manifest,
        )
        startup = ServiceStartup(
            mode=STARTUP_MODE_ROOT,
            namespace=namespace,
            root_path=str(Path(root_path)),
            manifest_path=str(manifest_path or ""),
            snapshot_out_path=str(snapshot_out_path or ""),
            manifest_out_path=str(manifest_out_path or ""),
        )
        service = cls(
            snapshot=refresh.snapshot,
            startup=startup,
            manifest=refresh.manifest,
        )
        service._persist_state()
        return service

    @property
    def snapshot(self) -> GraphSnapshot:
        return self._snapshot

    @property
    def refresh_supported(self) -> bool:
        return self._startup.mode == STARTUP_MODE_ROOT and bool(self._startup.root_path)

    def capabilities(self) -> ServiceCapabilities:
        import pragmagraph

        methods = list(SERVICE_METHODS)
        if not self.refresh_supported:
            methods.remove(METHOD_REFRESH)
        return ServiceCapabilities(
            service_version=SERVICE_VERSION,
            package_version=pragmagraph.__version__,
            package_status=pragmagraph.PACKAGE_STATUS,
            startup_mode=self._startup.mode,
            namespace=self._snapshot.namespace,
            refresh_supported=self.refresh_supported,
            supported_methods=tuple(methods),
            snapshot_schema_version=SCHEMA_VERSION,
            indexer_version=INDEXER_VERSION,
            graphify_format=GRAPHIFY_INTEROP_FORMAT,
        )

    def handle_request(self, request: ServiceRequest) -> tuple[ServiceResponse, bool]:
        try:
            result = self._dispatch(request)
        except PragmaGraphError as exc:
            return (
                ServiceResponse.failure(
                    request.id,
                    code=str(exc.code),
                    message=str(exc.message),
                    details=exc.details,
                ),
                False,
            )
        except Exception as exc:  # pragma: no cover - defensive envelope
            return (
                ServiceResponse.failure(
                    request.id,
                    code=ERROR_INTERNAL,
                    message="internal service error",
                    details={"error_type": type(exc).__name__},
                ),
                False,
            )
        should_shutdown = request.method == METHOD_SHUTDOWN
        return ServiceResponse.success(request.id, result), should_shutdown

    def _dispatch(self, request: ServiceRequest) -> Any:
        method = request.method
        if method == METHOD_CAPABILITIES:
            return self.capabilities().to_dict()
        if method == METHOD_HEALTH:
            return health(self._snapshot).to_dict()
        if method in {METHOD_QUERY, METHOD_EXPLAIN}:
            return self._query_result(request.params).to_dict()
        if method == METHOD_NEIGHBORHOOD:
            node_id = self._required_str(request.params, "node_id")
            if node_id not in self._snapshot.node_map():
                raise self._error(
                    ERROR_NOT_FOUND,
                    "requested node_id is not present in the loaded snapshot",
                    {"node_id": node_id},
                )
            depth = self._int_param(request.params, "depth", default=1, minimum=1)
            max_results = self._int_param(
                request.params,
                "max_results",
                default=10,
                minimum=1,
            )
            return neighborhood(
                self._snapshot,
                node_id,
                depth=depth,
                max_results=max_results,
            ).to_dict()
        if method == METHOD_PATH:
            source_id = self._required_str(request.params, "source_id")
            target_id = self._required_str(request.params, "target_id")
            node_map = self._snapshot.node_map()
            if source_id not in node_map:
                raise self._error(
                    ERROR_NOT_FOUND,
                    "requested source_id is not present in the loaded snapshot",
                    {"source_id": source_id},
                )
            if target_id not in node_map:
                raise self._error(
                    ERROR_NOT_FOUND,
                    "requested target_id is not present in the loaded snapshot",
                    {"target_id": target_id},
                )
            max_hops = self._int_param(
                request.params,
                "max_hops",
                default=4,
                minimum=1,
            )
            return path(
                self._snapshot,
                source_id,
                target_id,
                max_hops=max_hops,
            ).to_dict()
        if method == METHOD_REPORT:
            report = build_report(
                self._snapshot,
                top_n=self._int_param(request.params, "top_n", default=10, minimum=1),
            )
            format_name = self._str_param(request.params, "format", default="json")
            if format_name == "markdown":
                return {"format": "markdown", "text": render_markdown_report(report)}
            if format_name != "json":
                raise self._error(
                    ERROR_INVALID_PARAMS,
                    "report format must be 'json' or 'markdown'",
                    {"format": format_name},
                )
            return {"format": "json", "report": report.to_dict()}
        if method == METHOD_EXPORT:
            format_name = self._str_param(request.params, "format", default="dot")
            return {
                "format": format_name,
                "text": render_graph_export(self._snapshot, format=format_name),
            }
        if method == METHOD_GRAPHIFY_EXPORT:
            return to_graphify_payload(self._snapshot)
        if method == METHOD_REFRESH:
            return self._refresh_result()
        if method == METHOD_SHUTDOWN:
            return {"shutdown": "accepted"}
        raise self._error(
            ERROR_UNSUPPORTED_METHOD,
            "requested method is not supported by the local service",
            {"method": method},
        )

    def _query_result(self, params: Mapping[str, Any]) -> Any:
        request = QueryRequest(
            query=self._str_param(params, "text", default=""),
            node_ids=self._str_tuple_param(params, "node_ids"),
            max_results=self._int_param(params, "max_results", default=10, minimum=1),
            include_edges=self._bool_param(params, "include_edges", default=True),
        )
        return query(self._snapshot, request)

    def _refresh_result(self) -> dict[str, Any]:
        if not self.refresh_supported:
            raise self._error(
                ERROR_REFRESH_UNSUPPORTED,
                "refresh is unavailable for snapshot-backed service startup",
                {"startup_mode": self._startup.mode},
            )
        refresh = refresh_snapshot(
            self._startup.root_path,
            namespace=self._startup.namespace,
            previous_manifest=self._manifest,
        )
        self._snapshot = refresh.snapshot
        self._manifest = refresh.manifest
        self._persist_state()
        return {
            "changed_paths": list(refresh.changed_paths),
            "unchanged_paths": list(refresh.unchanged_paths),
            "removed_paths": list(refresh.removed_paths),
            "health": health(refresh.snapshot).to_dict(),
        }

    def _persist_state(self) -> None:
        if self._startup.snapshot_out_path:
            save_snapshot(self._snapshot, self._startup.snapshot_out_path)
        if self._startup.manifest_out_path and self._manifest is not None:
            save_manifest(self._manifest, self._startup.manifest_out_path)

    def _required_str(self, params: Mapping[str, Any], key: str) -> str:
        value = params.get(key)
        if not isinstance(value, str) or not value.strip():
            raise self._error(
                ERROR_INVALID_PARAMS,
                f"{key} must be a non-empty string",
                {key: value},
            )
        return value.strip()

    def _str_param(self, params: Mapping[str, Any], key: str, *, default: str) -> str:
        value = params.get(key, default)
        if not isinstance(value, str):
            raise self._error(
                ERROR_INVALID_PARAMS,
                f"{key} must be a string",
                {key: value},
            )
        text = value.strip()
        return text or default

    def _int_param(
        self,
        params: Mapping[str, Any],
        key: str,
        *,
        default: int,
        minimum: int,
    ) -> int:
        value = params.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise self._error(
                ERROR_INVALID_PARAMS,
                f"{key} must be an integer",
                {key: value},
            )
        if value < minimum:
            raise self._error(
                ERROR_INVALID_PARAMS,
                f"{key} must be >= {minimum}",
                {key: value},
            )
        return value

    def _bool_param(
        self,
        params: Mapping[str, Any],
        key: str,
        *,
        default: bool,
    ) -> bool:
        value = params.get(key, default)
        if not isinstance(value, bool):
            raise self._error(
                ERROR_INVALID_PARAMS,
                f"{key} must be a boolean",
                {key: value},
            )
        return value

    def _str_tuple_param(self, params: Mapping[str, Any], key: str) -> tuple[str, ...]:
        value = params.get(key, ())
        if value is None:
            return ()
        if isinstance(value, (list, tuple)) and all(
            isinstance(item, str) for item in value
        ):
            return tuple(item.strip() for item in value if item.strip())
        raise self._error(
            ERROR_INVALID_PARAMS,
            f"{key} must be an array of strings",
            {key: value},
        )

    def _error(
        self,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> PragmaGraphError:
        return PragmaGraphError(message, code=code, details=details or {})


__all__ = ["LocalQueryService", "ServiceStartup"]
