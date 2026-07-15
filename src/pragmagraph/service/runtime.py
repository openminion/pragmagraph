"""Transport-neutral runtime for the PragmaGraph local service surface."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from pragmagraph.adapters.git_history import DEFAULT_GIT_IDENTITY_MODE
from pragmagraph.contracts import INDEXER_VERSION, SCHEMA_VERSION
from pragmagraph.export import (
    EXPORT_PROFILES,
    EXPORT_SCHEMA_VERSION,
    project_snapshot,
    render_graph_export,
)
from pragmagraph.graphify import GRAPHIFY_INTEROP_FORMAT, to_graphify_payload
from pragmagraph.incremental import load_extraction_cache, save_extraction_cache
from pragmagraph.incremental.models import ExtractionCacheBundle
from pragmagraph.models import (
    GraphSnapshot,
    PragmaGraphError,
    QueryRequest,
    RefreshManifest,
)
from pragmagraph.operations import (
    RefreshProfile,
    RefreshStatus,
    refresh_status_from_result,
    save_refresh_status,
)
from pragmagraph.query import health, neighborhood, path, query
from pragmagraph.refresh import (
    load_manifest,
    refresh_snapshot,
    refresh_snapshot_incremental,
    save_manifest,
)
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
    STARTUP_MODE_STORE,
    STARTUP_MODE_WORKSPACE,
)
from pragmagraph.service.models import (
    ServiceCapabilities,
    ServiceRequest,
    ServiceResponse,
)
from pragmagraph.storage import (
    GraphStore,
    SQLiteGraphStore,
    load_snapshot,
    save_snapshot,
    stable_dumps,
)
from pragmagraph.workspace import (
    ensure_workspace_snapshot,
    load_workspace_status,
    refresh_workspace,
)

_CacheLoad = tuple[ExtractionCacheBundle | None, str]


def _load_cache(path: str | Path | None) -> _CacheLoad:
    if not path or not Path(path).exists():
        return None, ""
    try:
        return load_extraction_cache(path), ""
    except PragmaGraphError as exc:
        return None, exc.code.lower()


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
    state_out_path: str = ""
    workspace_path: str = ""
    store_path: str = ""
    profile_label: str = "service-root"
    cache_path: str = ""


class LocalQueryService:
    """One long-lived local graph service over a single active snapshot."""

    def __init__(
        self,
        *,
        snapshot: GraphSnapshot,
        startup: ServiceStartup,
        manifest: RefreshManifest | None = None,
        refresh_status: RefreshStatus | None = None,
        store: GraphStore | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._startup = startup
        self._manifest = manifest
        self._refresh_status = refresh_status
        self._store = store

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
    def from_store_path(cls, store_path: str | Path) -> "LocalQueryService":
        store = SQLiteGraphStore(store_path)
        snapshot = store.export_snapshot()
        return cls(
            snapshot=snapshot,
            startup=ServiceStartup(
                mode=STARTUP_MODE_STORE,
                namespace=snapshot.namespace,
                store_path=str(Path(store_path)),
            ),
            store=store,
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
        state_out_path: str | Path | None = None,
        cache_path: str | Path | None = None,
        git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
    ) -> "LocalQueryService":
        loaded_manifest = None
        if manifest_path and Path(manifest_path).exists():
            loaded_manifest = load_manifest(manifest_path)
        previous_snapshot = None
        if snapshot_out_path and Path(snapshot_out_path).exists():
            previous_snapshot = load_snapshot(snapshot_out_path)
        previous_cache, cache_fallback_reason = _load_cache(cache_path)
        if cache_path:
            refresh, next_cache = refresh_snapshot_incremental(
                root_path,
                namespace=namespace,
                previous_manifest=loaded_manifest,
                previous_snapshot=previous_snapshot,
                previous_cache=previous_cache,
                git_identity_mode=git_identity_mode,
            )
            if cache_fallback_reason:
                refresh = replace(
                    refresh,
                    work=replace(
                        refresh.work,
                        cache_fallback_reason=cache_fallback_reason,
                    ),
                )
        else:
            refresh = refresh_snapshot(
                root_path,
                namespace=namespace,
                previous_manifest=loaded_manifest,
                previous_snapshot=previous_snapshot,
                git_identity_mode=git_identity_mode,
            )
        startup = ServiceStartup(
            mode=STARTUP_MODE_ROOT,
            namespace=namespace,
            root_path=str(Path(root_path)),
            manifest_path=str(manifest_path or ""),
            snapshot_out_path=str(snapshot_out_path or ""),
            manifest_out_path=str(manifest_out_path or ""),
            state_out_path=str(state_out_path or ""),
            profile_label="service-root",
            cache_path=str(cache_path or ""),
        )
        refresh_status = refresh_status_from_result(
            profile=RefreshProfile(
                label="service-root",
                root_path=str(Path(root_path).resolve()),
                namespace=namespace,
                snapshot_path=startup.snapshot_out_path,
                manifest_path=startup.manifest_out_path or startup.manifest_path,
                state_path=startup.state_out_path,
                git_identity_mode=git_identity_mode,
            ),
            result=refresh,
        )
        service = cls(
            snapshot=refresh.snapshot,
            startup=startup,
            manifest=refresh.manifest,
            refresh_status=refresh_status,
        )
        service._persist_state()
        if cache_path:
            save_extraction_cache(next_cache, cache_path)
        return service

    @classmethod
    def from_workspace(cls, workspace_path: str | Path) -> "LocalQueryService":
        metadata = ensure_workspace_snapshot(workspace_path)
        snapshot = load_snapshot(metadata.paths.snapshot_path)
        manifest = None
        if Path(metadata.paths.manifest_path).exists():
            manifest = load_manifest(metadata.paths.manifest_path)
        refresh_status = load_workspace_status(workspace_path).refresh_status
        return cls(
            snapshot=snapshot,
            startup=ServiceStartup(
                mode=STARTUP_MODE_WORKSPACE,
                namespace=metadata.namespace,
                root_path=metadata.root_path,
                snapshot_path=metadata.paths.snapshot_path,
                manifest_path=metadata.paths.manifest_path,
                snapshot_out_path=metadata.paths.snapshot_path,
                manifest_out_path=metadata.paths.manifest_path,
                state_out_path=metadata.paths.status_path,
                workspace_path=metadata.paths.workspace_path,
                profile_label=metadata.label,
                cache_path=metadata.paths.cache_path,
            ),
            manifest=manifest,
            refresh_status=refresh_status,
        )

    @property
    def snapshot(self) -> GraphSnapshot:
        return self._snapshot

    @property
    def refresh_supported(self) -> bool:
        return self._startup.mode in {
            STARTUP_MODE_ROOT,
            STARTUP_MODE_WORKSPACE,
        } and bool(self._startup.root_path)

    def capabilities(self) -> ServiceCapabilities:
        import pragmagraph

        methods = list(SERVICE_METHODS)
        if not self.refresh_supported:
            methods.remove(METHOD_REFRESH)
        parser_set = tuple(
            self._snapshot.stats.get("parser_set", ())
            or sorted(
                {
                    str(node.metadata.get("parser"))
                    for node in self._snapshot.nodes
                    if node.metadata.get("parser")
                }
            )
        )
        parser_versions = tuple(
            self._snapshot.stats.get("parser_versions", ())
            or sorted(
                {
                    f"{node.metadata.get('parser')}:{node.metadata.get('parser_version')}"
                    for node in self._snapshot.nodes
                    if node.metadata.get("parser")
                    and node.metadata.get("parser_version")
                }
            )
        )
        store_manifest = self._store.manifest() if self._store is not None else None
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
            export_schema_version=EXPORT_SCHEMA_VERSION,
            manifest_schema_version=(
                self._manifest.schema_version if self._manifest is not None else ""
            ),
            parser_set=parser_set,
            parser_versions=parser_versions,
            export_formats=("dot", "mermaid"),
            export_profiles=tuple(EXPORT_PROFILES),
            report_formats=("json", "markdown"),
            snapshot_id=_snapshot_id(self._snapshot),
            root_path=self._startup.root_path or self._snapshot.root_path,
            snapshot_path=self._startup.snapshot_path,
            workspace_path=self._startup.workspace_path,
            git_overlay_supported=bool(
                self._snapshot.stats.get("git_overlay_enabled", False)
            ),
            git_identity_mode=str(
                self._snapshot.stats.get("git_identity_mode", "") or ""
            ),
            git_commit_count=int(self._snapshot.stats.get("git_commit_count", 0) or 0),
            git_changed_path_count=int(
                self._snapshot.stats.get("git_changed_path_count", 0) or 0
            ),
            store_backend=store_manifest.backend if store_manifest is not None else "",
            store_path=self._startup.store_path,
            store_manifest_schema_version=(
                store_manifest.manifest_schema_version
                if store_manifest is not None
                else ""
            ),
            store_fts_available=(
                store_manifest.fts_available if store_manifest is not None else False
            ),
        )

    def current_refresh_status(self) -> RefreshStatus | None:
        return self._refresh_status

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
            capabilities = self.capabilities()
            summary = self._store_health().to_dict()
            summary["service"] = {
                "startup_mode": self._startup.mode,
                "refresh_supported": self.refresh_supported,
                "snapshot_id": _snapshot_id(self._snapshot),
                "workspace_path": self._startup.workspace_path,
                "store_path": self._startup.store_path,
                "manifest_schema_version": (
                    self._manifest.schema_version if self._manifest is not None else ""
                ),
                "parser_set": capabilities.parser_set,
                "parser_versions": capabilities.parser_versions,
                "diagnostic_counts": _diagnostic_counts(self._snapshot),
                "git_overlay": self._git_overlay_summary(),
                "refresh_state": self._refresh_state_payload(),
                "store": self._store_summary(),
            }
            return summary
        if method in {METHOD_QUERY, METHOD_EXPLAIN}:
            return self._query_result(request.params).to_dict()
        if method == METHOD_NEIGHBORHOOD:
            node_id = self._required_str(request.params, "node_id")
            self._require_snapshot_node(node_id, detail_key="node_id")
            depth = self._int_param(request.params, "depth", default=1, minimum=1)
            max_results = self._int_param(
                request.params,
                "max_results",
                default=10,
                minimum=1,
            )
            return self._store_neighborhood(
                node_id,
                depth=depth,
                max_results=max_results,
                edge_kinds=self._str_tuple_param(request.params, "edge_kinds"),
                node_kinds=self._str_tuple_param(request.params, "node_kinds"),
            ).to_dict()
        if method == METHOD_PATH:
            source_id = self._required_str(request.params, "source_id")
            target_id = self._required_str(request.params, "target_id")
            self._require_snapshot_node(source_id, detail_key="source_id")
            self._require_snapshot_node(target_id, detail_key="target_id")
            max_hops = self._int_param(
                request.params,
                "max_hops",
                default=4,
                minimum=1,
            )
            return self._store_path(
                source_id,
                target_id,
                max_hops=max_hops,
                edge_kinds=self._str_tuple_param(request.params, "edge_kinds"),
                node_kinds=self._str_tuple_param(request.params, "node_kinds"),
            ).to_dict()
        if method == METHOD_REPORT:
            return self._report_result(request.params)
        if method == METHOD_EXPORT:
            return self._export_result(request.params)
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

    def _report_result(self, params: Mapping[str, Any]) -> dict[str, Any]:
        report = build_report(
            self._snapshot,
            top_n=self._int_param(params, "top_n", default=10, minimum=1),
        )
        format_name = self._str_param(params, "format", default="json")
        if format_name == "markdown":
            return {"format": "markdown", "text": render_markdown_report(report)}
        if format_name != "json":
            raise self._error(
                ERROR_INVALID_PARAMS,
                "report format must be 'json' or 'markdown'",
                {"format": format_name},
            )
        return {"format": "json", "report": report.to_dict()}

    def _export_result(self, params: Mapping[str, Any]) -> dict[str, Any]:
        format_name = self._str_param(params, "format", default="dot")
        profile = self._str_param(params, "profile", default="full")
        try:
            projection = project_snapshot(self._snapshot, profile=profile)
        except ValueError as exc:
            raise self._error(
                ERROR_INVALID_PARAMS,
                str(exc),
                {"profile": profile},
            ) from exc
        return {
            "format": format_name,
            "profile": profile,
            "redacted_fields": list(projection.redacted_fields),
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "snapshot_schema_version": self._snapshot.schema_version,
            "text": render_graph_export(projection.snapshot, format=format_name),
        }

    def _query_result(self, params: Mapping[str, Any]) -> Any:
        request = QueryRequest(
            query=self._str_param(params, "text", default=""),
            node_ids=self._str_tuple_param(params, "node_ids"),
            max_results=self._int_param(params, "max_results", default=10, minimum=1),
            include_edges=self._bool_param(params, "include_edges", default=True),
            cursor=self._str_param(params, "cursor", default=""),
            max_examined=self._optional_int_param(
                params,
                "max_examined",
                minimum=1,
            ),
        )
        if self._store is not None:
            return self._store.query(request)
        return query(self._snapshot, request)

    def _store_health(self) -> Any:
        return (
            self._store.health() if self._store is not None else health(self._snapshot)
        )

    def _store_neighborhood(
        self,
        node_id: str,
        *,
        depth: int,
        max_results: int,
        edge_kinds: tuple[str, ...],
        node_kinds: tuple[str, ...],
    ) -> Any:
        if self._store is not None:
            return self._store.neighborhood(
                node_id,
                depth=depth,
                max_results=max_results,
                edge_kinds=edge_kinds,
                node_kinds=node_kinds,
            )
        return neighborhood(
            self._snapshot,
            node_id,
            depth=depth,
            max_results=max_results,
            edge_kinds=edge_kinds,
            node_kinds=node_kinds,
        )

    def _store_path(
        self,
        source_id: str,
        target_id: str,
        *,
        max_hops: int,
        edge_kinds: tuple[str, ...],
        node_kinds: tuple[str, ...],
    ) -> Any:
        if self._store is not None:
            return self._store.path(
                source_id,
                target_id,
                max_hops=max_hops,
                edge_kinds=edge_kinds,
                node_kinds=node_kinds,
            )
        return path(
            self._snapshot,
            source_id,
            target_id,
            max_hops=max_hops,
            edge_kinds=edge_kinds,
            node_kinds=node_kinds,
        )

    def _require_snapshot_node(self, node_id: str, *, detail_key: str) -> None:
        if node_id in self._snapshot.node_map():
            return
        raise self._error(
            ERROR_NOT_FOUND,
            f"requested {detail_key} is not present in the loaded snapshot",
            {detail_key: node_id},
        )

    def _refresh_result(self) -> dict[str, Any]:
        if not self.refresh_supported:
            raise self._error(
                ERROR_REFRESH_UNSUPPORTED,
                "refresh is unavailable for snapshot-backed service startup",
                {"startup_mode": self._startup.mode},
            )
        if (
            self._startup.mode == STARTUP_MODE_WORKSPACE
            and self._startup.workspace_path
        ):
            workspace_result = refresh_workspace(self._startup.workspace_path)
            refresh = workspace_result.operation.result
            self._snapshot = refresh.snapshot
            self._manifest = refresh.manifest
            self._refresh_status = workspace_result.operation.status
        else:
            if self._startup.cache_path:
                previous_cache, cache_fallback_reason = _load_cache(
                    self._startup.cache_path
                )
                refresh, next_cache = refresh_snapshot_incremental(
                    self._startup.root_path,
                    namespace=self._startup.namespace,
                    previous_manifest=self._manifest,
                    previous_snapshot=self._snapshot,
                    previous_cache=previous_cache,
                    git_identity_mode=self._git_identity_mode(),
                )
                if cache_fallback_reason:
                    refresh = replace(
                        refresh,
                        work=replace(
                            refresh.work,
                            cache_fallback_reason=cache_fallback_reason,
                        ),
                    )
            else:
                refresh = refresh_snapshot(
                    self._startup.root_path,
                    namespace=self._startup.namespace,
                    previous_manifest=self._manifest,
                    previous_snapshot=self._snapshot,
                    git_identity_mode=self._git_identity_mode(),
                )
            self._snapshot = refresh.snapshot
            self._manifest = refresh.manifest
            self._refresh_status = refresh_status_from_result(
                profile=RefreshProfile(
                    label=self._startup.profile_label,
                    root_path=self._startup.root_path,
                    namespace=self._startup.namespace,
                    snapshot_path=self._startup.snapshot_out_path,
                    manifest_path=(
                        self._startup.manifest_out_path or self._startup.manifest_path
                    ),
                    state_path=self._startup.state_out_path,
                    git_identity_mode=self._git_identity_mode(),
                ),
                result=refresh,
            )
            self._persist_state()
            if self._startup.cache_path:
                save_extraction_cache(next_cache, self._startup.cache_path)
        return {
            "changed_paths": list(refresh.changed_paths),
            "unchanged_paths": list(refresh.unchanged_paths),
            "removed_paths": list(refresh.removed_paths),
            "path_changes": [item.to_dict() for item in refresh.path_changes],
            "snapshot_delta": refresh.snapshot_delta.to_dict(),
            "identity_transitions": [
                item.to_dict() for item in refresh.identity_transitions
            ],
            "work": refresh.work.to_dict(),
            "health": health(refresh.snapshot).to_dict(),
            "refresh_state": self._refresh_state_payload(),
        }

    def _persist_state(self) -> None:
        if self._startup.snapshot_out_path:
            save_snapshot(self._snapshot, self._startup.snapshot_out_path)
        if self._startup.manifest_out_path and self._manifest is not None:
            save_manifest(self._manifest, self._startup.manifest_out_path)
        if self._startup.state_out_path and self._refresh_status is not None:
            save_refresh_status(self._refresh_status, self._startup.state_out_path)

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

    def _optional_int_param(
        self,
        params: Mapping[str, Any],
        key: str,
        *,
        minimum: int,
    ) -> int | None:
        if key not in params or params[key] is None:
            return None
        return self._int_param(params, key, default=minimum, minimum=minimum)

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

    def _refresh_state_payload(self) -> dict[str, Any] | None:
        return (
            self._refresh_status.to_dict() if self._refresh_status is not None else None
        )

    def _git_identity_mode(self) -> str:
        return str(
            self._snapshot.stats.get(
                "git_identity_mode",
                DEFAULT_GIT_IDENTITY_MODE,
            )
            or DEFAULT_GIT_IDENTITY_MODE
        )

    def _git_overlay_summary(self) -> dict[str, Any]:
        return {
            "enabled": bool(self._snapshot.stats.get("git_overlay_enabled", False)),
            "identity_mode": str(
                self._snapshot.stats.get("git_identity_mode", "") or ""
            ),
            "commit_count": int(self._snapshot.stats.get("git_commit_count", 0) or 0),
            "changed_path_count": int(
                self._snapshot.stats.get("git_changed_path_count", 0) or 0
            ),
        }

    def _store_summary(self) -> dict[str, Any] | None:
        if self._store is None:
            return None
        manifest = self._store.manifest()
        capabilities = self._store.capabilities()
        return {
            "backend": manifest.backend,
            "path": self._startup.store_path,
            "manifest_schema_version": manifest.manifest_schema_version,
            "schema_version": manifest.schema_version,
            "fts_available": manifest.fts_available,
            "capabilities": capabilities.to_dict(),
        }


def _snapshot_id(snapshot: GraphSnapshot) -> str:
    return hashlib.sha256(stable_dumps(snapshot).encode("utf-8")).hexdigest()[:16]


def _diagnostic_counts(snapshot: GraphSnapshot) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in snapshot.omitted:
        counts[item.reason] = counts.get(item.reason, 0) + 1
    return dict(sorted(counts.items()))


__all__ = ["LocalQueryService", "ServiceStartup"]
