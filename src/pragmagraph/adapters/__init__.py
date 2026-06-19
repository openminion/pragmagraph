"""Local filesystem indexer adapters for PragmaGraph."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, Iterable, Mapping

from pragmagraph.adapters.git_history import (
    DEFAULT_GIT_IDENTITY_MODE,
    SUPPORTED_GIT_IDENTITY_MODES,
    collect_git_overlay,
    validate_git_identity_mode,
)
from pragmagraph.contracts import (
    EDGE_CONTAINS,
    EDGE_DEFINES,
    EDGE_DEPENDS_ON,
    EDGE_HAS_KEY,
    EDGE_IMPORTS,
    EDGE_REFERENCES_DOC,
    EDGE_REFERENCES_SECTION,
    INDEXER_VERSION,
    NODE_CONFIG,
    NODE_CONFIG_KEY,
    NODE_DIRECTORY,
    NODE_DOC_SECTION,
    NODE_FILE,
    NODE_IMPORT,
    NODE_PROJECT,
    SCHEMA_VERSION,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OmittedDiagnostic,
    SourceRef,
)
from pragmagraph.parsers import ParserRegistry, get_default_registry
from pragmagraph.portability import edge_id, node_id, normalize_relative_path
from pragmagraph.security import (
    DEFAULT_IGNORES,
    TEXT_SUFFIXES,
    ScopePolicy,
    escape_label,
    load_gitignore,
    should_index_path,
)

CONFIG_NAMES = frozenset({"package.json", "pyproject.toml"})
CONFIG_SUFFIXES = frozenset({".json", ".toml", ".yaml", ".yml"})


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _rel(path: Path, root: Path) -> str:
    return normalize_relative_path(path.relative_to(root))


def _snippet(text: str, *, limit: int = 360) -> str:
    collapsed = " ".join(text.strip().split())
    return collapsed[:limit]


def _markdown_slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "section"


def _add_node(nodes: dict[str, GraphNode], node: GraphNode) -> None:
    nodes.setdefault(node.id, node)


def _add_edge(edges: dict[str, GraphEdge], edge: GraphEdge) -> None:
    edges.setdefault(edge.id, edge)


def _omitted(
    *,
    reason: str,
    item_id: str,
    details: Mapping[str, Any] | None = None,
) -> OmittedDiagnostic:
    return OmittedDiagnostic(reason=reason, item_id=item_id, details=details or {})


def _parser_provenance(
    nodes: dict[str, GraphNode],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    parser_set = tuple(
        sorted(
            {
                str(node.metadata.get("parser"))
                for node in nodes.values()
                if node.metadata.get("parser")
            }
        )
    )
    parser_versions = tuple(
        sorted(
            {
                f"{node.metadata.get('parser')}:{node.metadata.get('parser_version')}"
                for node in nodes.values()
                if node.metadata.get("parser") and node.metadata.get("parser_version")
            }
        )
    )
    return parser_set, parser_versions


def _iter_paths(
    root: Path, policy: ScopePolicy
) -> Iterable[tuple[Path, OmittedDiagnostic | None]]:
    gitignore_patterns = load_gitignore(root) if policy.respect_gitignore else ()
    for path in sorted(root.rglob("*")):
        allowed, diagnostic = should_index_path(
            path,
            root,
            policy,
            gitignore_patterns=gitignore_patterns,
        )
        if diagnostic is not None:
            yield (
                path,
                _omitted(
                    reason=diagnostic.code,
                    item_id=diagnostic.path,
                    details=diagnostic.to_dict(),
                ),
            )
        if allowed:
            yield path, None


def index_path(
    root_path: str | Path,
    *,
    namespace: str = "default",
    ignore_names: frozenset[str] = DEFAULT_IGNORES,
    created_at: str = "",
    policy: ScopePolicy | None = None,
    parser_registry: ParserRegistry | None = None,
    git_identity_mode: str = DEFAULT_GIT_IDENTITY_MODE,
) -> GraphSnapshot:
    """Index a local code/docs root into a deterministic snapshot."""
    root = Path(root_path).resolve()
    scope = policy or ScopePolicy(ignore_names=ignore_names)
    registry = parser_registry or get_default_registry()
    identity_mode = validate_git_identity_mode(git_identity_mode)
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    omitted: list[OmittedDiagnostic] = []

    project_id = node_id(namespace, NODE_PROJECT, ".")
    _add_node(
        nodes,
        GraphNode(
            id=project_id,
            kind=NODE_PROJECT,
            label=root.name or namespace,
            source_ref=SourceRef(path="."),
            metadata={"namespace": namespace},
        ),
    )

    parent_by_path: dict[str, str] = {"": project_id}
    for path, diagnostic in _iter_paths(root, scope):
        if diagnostic is not None:
            omitted.append(diagnostic)
            continue
        rel = _rel(path, root)
        parent_rel = normalize_relative_path(Path(rel).parent)
        parent_id = parent_by_path.get(parent_rel, project_id)
        if path.is_dir():
            current_id = node_id(namespace, NODE_DIRECTORY, rel)
            parent_by_path[rel] = current_id
            _add_node(
                nodes,
                GraphNode(
                    id=current_id,
                    kind=NODE_DIRECTORY,
                    label=escape_label(path.name),
                    source_ref=SourceRef(path=rel),
                ),
            )
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, parent_id, EDGE_CONTAINS, current_id),
                    kind=EDGE_CONTAINS,
                    source_id=parent_id,
                    target_id=current_id,
                    source_ref=SourceRef(path=rel),
                ),
            )
            continue
        if not path.is_file():
            continue
        file_id = node_id(namespace, NODE_FILE, rel)
        text = _read_text(path) if path.suffix.lower() in TEXT_SUFFIXES else ""
        _add_node(
            nodes,
            GraphNode(
                id=file_id,
                kind=NODE_FILE,
                label=escape_label(path.name),
                source_ref=SourceRef(path=rel),
                text=_snippet(text),
                metadata={
                    "content_hash": _content_hash(path),
                    "suffix": path.suffix.lower(),
                },
            ),
        )
        _add_edge(
            edges,
            GraphEdge(
                id=edge_id(namespace, parent_id, EDGE_CONTAINS, file_id),
                kind=EDGE_CONTAINS,
                source_id=parent_id,
                target_id=file_id,
                source_ref=SourceRef(path=rel),
            ),
        )
        _index_file(
            namespace=namespace,
            rel=rel,
            path=path,
            file_id=file_id,
            text=text,
            registry=registry,
            nodes=nodes,
            edges=edges,
            omitted=omitted,
        )

    _resolve_local_imports(namespace, nodes, edges, omitted)
    git_nodes, git_edges, git_omitted, git_stats = collect_git_overlay(
        root=root,
        namespace=namespace,
        nodes_by_id=nodes,
        git_identity_mode=identity_mode,
    )
    for node in git_nodes:
        _add_node(nodes, node)
    for edge in git_edges:
        _add_edge(edges, edge)
    omitted.extend(git_omitted)
    parser_set, parser_versions = _parser_provenance(nodes)
    stats = {
        "edge_count": len(edges),
        "git_changed_path_count": int(git_stats.get("git_changed_path_count", 0)),
        "git_commit_count": int(git_stats.get("git_commit_count", 0)),
        "git_identity_mode": str(git_stats.get("git_identity_mode", identity_mode)),
        "git_overlay_enabled": bool(git_stats.get("git_overlay_enabled", False)),
        "git_repo_root": str(git_stats.get("git_repo_root", "")),
        "git_root_prefix": str(git_stats.get("git_root_prefix", "")),
        "git_shallow_repository": bool(git_stats.get("git_shallow_repository", False)),
        "node_count": len(nodes),
        "omitted_count": len(omitted),
        "parser_set": parser_set,
        "parser_versions": parser_versions,
        "root_exists": root.exists(),
        "parser_count": len(registry.parsers),
        "scope_max_file_bytes": scope.max_file_bytes,
    }
    return GraphSnapshot(
        namespace=namespace,
        root_path=str(root),
        nodes=tuple(sorted(nodes.values(), key=lambda node: node.id)),
        edges=tuple(sorted(edges.values(), key=lambda edge: edge.id)),
        omitted=tuple(omitted),
        stats=stats,
        schema_version=SCHEMA_VERSION,
        indexer_version=INDEXER_VERSION,
        created_at=created_at,
    )


def _resolve_local_imports(
    namespace: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    modules = {
        str(node.metadata.get("module_name")): node.id
        for node in nodes.values()
        if node.kind in {"python_module", "script_module"}
        and node.metadata.get("module_name")
    }
    modules_by_path = {
        normalize_relative_path(Path(node.source_ref.path).with_suffix("")): node.id
        for node in nodes.values()
        if node.kind in {"python_module", "script_module"} and node.source_ref.path
    }
    for node in tuple(nodes.values()):
        if node.kind != NODE_IMPORT:
            continue
        target_id = modules.get(node.label)
        if target_id is None:
            target_id = _resolve_relative_module_id(node, modules_by_path)
        if target_id:
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, node.id, EDGE_IMPORTS, target_id),
                    kind=EDGE_IMPORTS,
                    source_id=node.id,
                    target_id=target_id,
                    source_ref=node.source_ref,
                    metadata={"resolved": True},
                ),
            )
        elif "." in node.label or str(node.metadata.get("source_path", "")).strip():
            omitted.append(
                _omitted(
                    reason="unresolved_local_import",
                    item_id=node.label,
                    details={"source_path": node.source_ref.path},
                )
            )


def _content_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_file(
    *,
    namespace: str,
    rel: str,
    path: Path,
    file_id: str,
    text: str,
    registry: ParserRegistry,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    if path.suffix.lower() == ".md":
        _index_markdown(namespace, rel, file_id, text, nodes, edges, omitted)
    if path.name in CONFIG_NAMES or path.suffix.lower() in CONFIG_SUFFIXES:
        _index_config(namespace, rel, file_id, text, nodes, edges, omitted)
    selection = registry.select_parser(path, rel=rel)
    parser = selection.parser
    for diagnostic in selection.diagnostics:
        omitted.append(
            _omitted(
                reason=diagnostic.code,
                item_id=diagnostic.path or rel,
                details=diagnostic.to_dict(),
            )
        )
    if parser is None:
        return
    result = parser.parse(namespace=namespace, rel=rel, file_id=file_id, text=text)
    for node in result.nodes:
        _add_node(nodes, node)
    for edge in result.edges:
        _add_edge(edges, edge)
    for diagnostic in result.diagnostics:
        omitted.append(
            _omitted(
                reason=diagnostic.code,
                item_id=diagnostic.path or rel,
                details=diagnostic.to_dict(),
            )
        )


def _resolve_relative_module_id(
    import_node: GraphNode,
    modules_by_path: dict[str, str],
) -> str | None:
    source_path = str(import_node.metadata.get("source_path", "") or "")
    label = import_node.label.strip()
    if not source_path or not label.startswith((".", "/")):
        return None
    base = Path(source_path).parent
    target = normalize_relative_path(base / label)
    candidates = (
        target,
        f"{target}/index",
    )
    for candidate in candidates:
        if candidate in modules_by_path:
            return modules_by_path[candidate]
    for suffix in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"):
        trimmed = target.removesuffix(suffix) if target.endswith(suffix) else ""
        if trimmed and trimmed in modules_by_path:
            return modules_by_path[trimmed]
    return None


def _index_markdown(
    namespace: str,
    rel: str,
    file_id: str,
    text: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    previous_by_level: dict[int, str] = {}
    section_by_slug: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            _index_markdown_links(
                namespace, rel, file_id, line, number, nodes, edges, omitted
            )
            continue
        level = len(match.group(1))
        heading = escape_label(match.group(2))
        slug = _markdown_slug(heading)
        section_id = node_id(namespace, NODE_DOC_SECTION, f"{rel}#{slug}")
        source_ref = SourceRef(path=rel, line=number, section=heading)
        _add_node(
            nodes,
            GraphNode(
                id=section_id,
                kind=NODE_DOC_SECTION,
                label=heading,
                source_ref=source_ref,
                text=heading,
                metadata={"level": level, "slug": slug, "anchor": f"#{slug}"},
            ),
        )
        _add_edge(
            edges,
            GraphEdge(
                id=edge_id(namespace, file_id, EDGE_DEFINES, section_id),
                kind=EDGE_DEFINES,
                source_id=file_id,
                target_id=section_id,
                source_ref=source_ref,
            ),
        )
        parent_id = _nearest_parent_section(previous_by_level, level)
        if parent_id:
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(
                        namespace, parent_id, EDGE_REFERENCES_SECTION, section_id
                    ),
                    kind=EDGE_REFERENCES_SECTION,
                    source_id=parent_id,
                    target_id=section_id,
                    source_ref=source_ref,
                ),
            )
        previous_by_level[level] = section_id
        section_by_slug[slug] = section_id
    _index_local_anchor_links(
        namespace, rel, text, section_by_slug, file_id, edges, omitted
    )


def _nearest_parent_section(previous_by_level: dict[int, str], level: int) -> str:
    for candidate in range(level - 1, 0, -1):
        if candidate in previous_by_level:
            return previous_by_level[candidate]
    return ""


def _index_markdown_links(
    namespace: str,
    rel: str,
    file_id: str,
    line: str,
    number: int,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", line):
        _add_doc_reference(
            namespace, rel, file_id, target, number, nodes, edges, omitted
        )
    for target in re.findall(r"\[\[([^\]]+)\]\]", line):
        _add_doc_reference(
            namespace, rel, file_id, target, number, nodes, edges, omitted
        )


def _add_doc_reference(
    namespace: str,
    rel: str,
    file_id: str,
    target: str,
    line: int,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    if target.startswith(("http://", "https://", "mailto:")):
        return
    normalized = target.replace("\\", "/").lstrip("./")
    if "#" in normalized:
        path_part, anchor = normalized.split("#", 1)
        slug = _markdown_slug(anchor)
        target_key = f"{path_part or rel}#{slug}"
    else:
        target_key = normalized
    if not target_key:
        return
    target_id = node_id(namespace, NODE_DOC_SECTION, target_key)
    _add_node(
        nodes,
        GraphNode(
            id=target_id,
            kind=NODE_DOC_SECTION,
            label=target_key,
            source_ref=SourceRef(path=target_key.split("#", 1)[0]),
            metadata={"unresolved": True},
        ),
    )
    _add_edge(
        edges,
        GraphEdge(
            id=edge_id(namespace, file_id, EDGE_REFERENCES_DOC, target_id),
            kind=EDGE_REFERENCES_DOC,
            source_id=file_id,
            target_id=target_id,
            source_ref=SourceRef(path=rel, line=line),
            metadata={"target": target},
        ),
    )
    omitted.append(
        _omitted(
            reason="unresolved_markdown_reference",
            item_id=target_key,
            details={"source_path": rel, "line": line, "target": target},
        )
    )


def _index_local_anchor_links(
    namespace: str,
    rel: str,
    text: str,
    section_by_slug: dict[str, str],
    file_id: str,
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    for number, line in enumerate(text.splitlines(), start=1):
        for target in re.findall(r"\[[^\]]+\]\(#([^)]+)\)", line):
            slug = _markdown_slug(target)
            target_id = section_by_slug.get(slug)
            if not target_id:
                omitted.append(
                    _omitted(
                        reason="unresolved_markdown_anchor",
                        item_id=f"{rel}#{slug}",
                        details={"source_path": rel, "line": number},
                    )
                )
                continue
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, file_id, EDGE_REFERENCES_DOC, target_id),
                    kind=EDGE_REFERENCES_DOC,
                    source_id=file_id,
                    target_id=target_id,
                    source_ref=SourceRef(path=rel, line=number),
                ),
            )


def _index_config(
    namespace: str,
    rel: str,
    file_id: str,
    text: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    config_id = node_id(namespace, NODE_CONFIG, rel)
    _add_node(
        nodes,
        GraphNode(
            id=config_id,
            kind=NODE_CONFIG,
            label=Path(rel).name,
            source_ref=SourceRef(path=rel),
            metadata={"format": Path(rel).suffix.lower().lstrip(".")},
        ),
    )
    _add_edge(
        edges,
        GraphEdge(
            id=edge_id(namespace, file_id, EDGE_DEFINES, config_id),
            kind=EDGE_DEFINES,
            source_id=file_id,
            target_id=config_id,
            source_ref=SourceRef(path=rel),
        ),
    )
    for key, value in _config_items(rel, text, omitted):
        key_id = node_id(namespace, NODE_CONFIG_KEY, f"{rel}:{key}")
        _add_node(
            nodes,
            GraphNode(
                id=key_id,
                kind=NODE_CONFIG_KEY,
                label=key,
                source_ref=SourceRef(path=rel),
                text=str(value)[:180],
                metadata={"value_type": type(value).__name__},
            ),
        )
        _add_edge(
            edges,
            GraphEdge(
                id=edge_id(namespace, config_id, EDGE_HAS_KEY, key_id),
                kind=EDGE_HAS_KEY,
                source_id=config_id,
                target_id=key_id,
                source_ref=SourceRef(path=rel),
            ),
        )
        for dependency in _dependency_values(key, value):
            dependency_id = node_id(
                namespace, NODE_CONFIG_KEY, f"dependency:{dependency}"
            )
            _add_node(
                nodes,
                GraphNode(
                    id=dependency_id,
                    kind=NODE_CONFIG_KEY,
                    label=dependency,
                    source_ref=SourceRef(path=rel),
                    metadata={"dependency": True},
                ),
            )
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, config_id, EDGE_DEPENDS_ON, dependency_id),
                    kind=EDGE_DEPENDS_ON,
                    source_id=config_id,
                    target_id=dependency_id,
                    source_ref=SourceRef(path=rel),
                ),
            )


def _config_items(
    rel: str,
    text: str,
    omitted: list[OmittedDiagnostic],
) -> tuple[tuple[str, Any], ...]:
    try:
        if rel.endswith(".json"):
            data = json.loads(text)
        elif rel.endswith(".toml"):
            data = tomllib.loads(text)
        elif rel.endswith((".yaml", ".yml")):
            data = _parse_simple_yaml(text)
        else:
            return ()
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, ValueError) as exc:
        omitted.append(
            _omitted(
                reason="config_parse_error",
                item_id=rel,
                details={"message": str(exc)},
            )
        )
        return ()
    return tuple(_flatten_mapping(data))


def _flatten_mapping(value: object, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in sorted(value.items()):
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_mapping(item, child)
    else:
        yield prefix, value


def _dependency_values(key: str, value: object) -> tuple[str, ...]:
    key_parts = set(key.split("."))
    if (
        not {
            "dependencies",
            "devDependencies",
            "optionalDependencies",
            "requires-python",
        }
        & key_parts
    ):
        return ()
    key_segments = key.split(".")
    if (
        isinstance(value, str)
        and len(key_segments) >= 2
        and key_segments[-2]
        in {
            "dependencies",
            "devDependencies",
            "optionalDependencies",
        }
    ):
        return (key_segments[-1],)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, str):
        return (value,)
    return ()


def _parse_simple_yaml(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


__all__ = [
    "CONFIG_NAMES",
    "CONFIG_SUFFIXES",
    "DEFAULT_IGNORES",
    "DEFAULT_GIT_IDENTITY_MODE",
    "SUPPORTED_GIT_IDENTITY_MODES",
    "TEXT_SUFFIXES",
    "index_path",
    "validate_git_identity_mode",
]
