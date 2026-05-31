"""Local filesystem indexer adapters for PragmaGraph."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path
from typing import Iterable

from pragmagraph.contracts import (
    EDGE_CONTAINS,
    EDGE_DEFINES,
    EDGE_IMPORTS,
    EDGE_REFERENCES_SECTION,
    INDEXER_VERSION,
    NODE_DIRECTORY,
    NODE_DOC_SECTION,
    NODE_FILE,
    NODE_PROJECT,
    NODE_PYTHON_SYMBOL,
    SCHEMA_VERSION,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    GraphSnapshot,
    OmittedDiagnostic,
    SourceRef,
)
from pragmagraph.portability import edge_id, node_id, normalize_relative_path

DEFAULT_IGNORES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)

TEXT_SUFFIXES = frozenset({".md", ".py", ".txt", ".rst"})


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _iter_paths(root: Path, ignore_names: frozenset[str]) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if any(part in ignore_names for part in path.relative_to(root).parts):
            continue
        yield path


def index_path(
    root_path: str | Path,
    *,
    namespace: str = "default",
    ignore_names: frozenset[str] = DEFAULT_IGNORES,
    created_at: str = "",
) -> GraphSnapshot:
    """Index a local code/docs root into a deterministic snapshot."""
    root = Path(root_path).resolve()
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
    for path in _iter_paths(root, ignore_names):
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
                    label=path.name,
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
                label=path.name,
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
        if path.suffix.lower() == ".md":
            _index_markdown(
                namespace=namespace,
                rel=rel,
                file_id=file_id,
                text=text,
                nodes=nodes,
                edges=edges,
            )
        elif path.suffix.lower() == ".py":
            _index_python(
                namespace=namespace,
                rel=rel,
                file_id=file_id,
                text=text,
                nodes=nodes,
                edges=edges,
                omitted=omitted,
            )

    stats = {
        "edge_count": len(edges),
        "node_count": len(nodes),
        "omitted_count": len(omitted),
        "root_exists": root.exists(),
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


def _index_markdown(
    *,
    namespace: str,
    rel: str,
    file_id: str,
    text: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
) -> None:
    previous_section_id = ""
    for number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        heading = match.group(2).strip()
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
                metadata={"level": len(match.group(1)), "slug": slug},
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
        if previous_section_id:
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(
                        namespace,
                        previous_section_id,
                        EDGE_REFERENCES_SECTION,
                        section_id,
                    ),
                    kind=EDGE_REFERENCES_SECTION,
                    source_id=previous_section_id,
                    target_id=section_id,
                    source_ref=source_ref,
                ),
            )
        previous_section_id = section_id


def _index_python(
    *,
    namespace: str,
    rel: str,
    file_id: str,
    text: str,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
    omitted: list[OmittedDiagnostic],
) -> None:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        omitted.append(
            OmittedDiagnostic(
                reason="python_syntax_error",
                item_id=rel,
                details={"line": exc.lineno, "message": exc.msg},
            )
        )
        return

    for item in ast.walk(tree):
        if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol_key = f"{rel}:{item.name}"
            symbol_id = node_id(namespace, NODE_PYTHON_SYMBOL, symbol_key)
            source_ref = SourceRef(path=rel, line=getattr(item, "lineno", None))
            _add_node(
                nodes,
                GraphNode(
                    id=symbol_id,
                    kind=NODE_PYTHON_SYMBOL,
                    label=item.name,
                    source_ref=source_ref,
                    text=item.name,
                    metadata={"symbol_type": type(item).__name__},
                ),
            )
            _add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, file_id, EDGE_DEFINES, symbol_id),
                    kind=EDGE_DEFINES,
                    source_id=file_id,
                    target_id=symbol_id,
                    source_ref=source_ref,
                ),
            )
        elif isinstance(item, ast.Import):
            for alias in item.names:
                _add_import_edge(
                    namespace=namespace,
                    rel=rel,
                    file_id=file_id,
                    module=alias.name,
                    line=getattr(item, "lineno", None),
                    nodes=nodes,
                    edges=edges,
                )
        elif isinstance(item, ast.ImportFrom) and item.module:
            _add_import_edge(
                namespace=namespace,
                rel=rel,
                file_id=file_id,
                module=item.module,
                line=getattr(item, "lineno", None),
                nodes=nodes,
                edges=edges,
            )


def _add_import_edge(
    *,
    namespace: str,
    rel: str,
    file_id: str,
    module: str,
    line: int | None,
    nodes: dict[str, GraphNode],
    edges: dict[str, GraphEdge],
) -> None:
    import_id = node_id(namespace, NODE_PYTHON_SYMBOL, f"import:{module}")
    source_ref = SourceRef(path=rel, line=line)
    _add_node(
        nodes,
        GraphNode(
            id=import_id,
            kind=NODE_PYTHON_SYMBOL,
            label=module,
            source_ref=SourceRef(path=rel, line=line),
            text=module,
            metadata={"external": True, "symbol_type": "import"},
        ),
    )
    _add_edge(
        edges,
        GraphEdge(
            id=edge_id(namespace, file_id, EDGE_IMPORTS, import_id),
            kind=EDGE_IMPORTS,
            source_id=file_id,
            target_id=import_id,
            source_ref=source_ref,
        ),
    )


__all__ = [
    "DEFAULT_IGNORES",
    "TEXT_SUFFIXES",
    "index_path",
]
