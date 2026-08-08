"""Optional precise script parser for observed JavaScript and TypeScript facts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pragmagraph.contracts import (
    EDGE_DEFINES,
    EDGE_IMPORTS,
    EDGE_PARENT_SYMBOL,
    NODE_IMPORT,
    NODE_SCRIPT_CLASS,
    NODE_SCRIPT_EXPORT,
    NODE_SCRIPT_FUNCTION,
    NODE_SCRIPT_MODULE,
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    ParserDiagnostic,
    ParserResult,
    SourceRef,
)
from pragmagraph.parsers.common import module_name, script_language
from pragmagraph.parsers.registry import SCRIPT_PRECISE_PARSER_VERSION, SCRIPT_SUFFIXES
from pragmagraph.parsers.script import ScriptLexicalParser
from pragmagraph.portability import edge_id, node_id


class ScriptTreeSitterParser:
    """Optional precise parser for JS/TS module structure."""

    name = "script_tree_sitter"
    version = SCRIPT_PRECISE_PARSER_VERSION
    suffixes = SCRIPT_SUFFIXES

    def __init__(self, parser_factory: Any, *, fallback: ScriptLexicalParser) -> None:
        self._parser_factory = parser_factory
        self._fallback = fallback
        self._parsers: dict[str, Any] = {}

    def parse(
        self, *, namespace: str, rel: str, file_id: str, text: str
    ) -> ParserResult:
        fallback = self._fallback.parse(
            namespace=namespace,
            rel=rel,
            file_id=file_id,
            text=text,
        )
        try:
            parser = self._parser_for_language(_tree_sitter_language(rel))
            root = _tree_root_node(_parse_tree(parser, text))
        except (AttributeError, LookupError, TypeError, ValueError) as exc:
            return self._fallback_result(
                fallback,
                rel=rel,
                reason="script_precise_parser_failed",
                details={"error_type": type(exc).__name__},
            )
        if _node_has_error(root):
            return self._fallback_result(
                fallback,
                rel=rel,
                reason="script_precise_parser_degraded",
                details={"reason": "syntax_error"},
            )

        nodes = {
            node.id: _with_script_parser_metadata(
                node,
                parser_name=self.name,
                parser_version=self.version,
            )
            for node in fallback.nodes
        }
        edges = {edge.id: edge for edge in fallback.edges}
        diagnostics = list(fallback.diagnostics)
        module_id = node_id(namespace, NODE_SCRIPT_MODULE, rel)

        for statement in _node_named_children(root):
            kind = _node_kind(statement)
            if kind == "import_statement":
                self._parse_import_statement(
                    namespace,
                    rel,
                    file_id,
                    statement,
                    text,
                    nodes,
                    edges,
                )
                continue
            if kind == "function_declaration":
                self._add_function_symbol(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    statement,
                    text,
                    nodes,
                    edges,
                    exported=False,
                )
                continue
            if kind == "class_declaration":
                self._add_class_symbol(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    statement,
                    text,
                    nodes,
                    edges,
                    exported=False,
                )
                continue
            if kind == "export_statement":
                self._parse_export_statement(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    statement,
                    text,
                    nodes,
                    edges,
                )

        return ParserResult(
            nodes=tuple(sorted(nodes.values(), key=lambda node: node.id)),
            edges=tuple(sorted(edges.values(), key=lambda edge: edge.id)),
            diagnostics=tuple(diagnostics),
        )

    def _parser_for_language(self, language: str) -> Any:
        parser = self._parsers.get(language)
        if parser is None:
            parser = self._parser_factory(language)
            self._parsers[language] = parser
        return parser

    def _fallback_result(
        self,
        fallback: ParserResult,
        *,
        rel: str,
        reason: str,
        details: dict[str, object],
    ) -> ParserResult:
        return ParserResult(
            nodes=fallback.nodes,
            edges=fallback.edges,
            diagnostics=(
                *fallback.diagnostics,
                ParserDiagnostic(
                    reason,
                    "precise parser fell back to the deterministic lexical parser",
                    rel,
                    details={
                        "parser": self.name,
                        "fallback_parser": self._fallback.name,
                        **details,
                    },
                ),
            ),
        )

    def _parse_import_statement(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        statement: Any,
        text: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        source = statement.child_by_field_name("source")
        if source is None:
            return
        module = _string_literal_value(source, text)
        if not module:
            return
        self._add_import_node(
            namespace,
            rel,
            file_id,
            module,
            _source_ref_from_node(rel, statement),
            nodes,
            edges,
        )

    def _parse_export_statement(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        statement: Any,
        text: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        source_ref = _source_ref_from_node(rel, statement)
        declaration = statement.child_by_field_name("declaration")
        source = statement.child_by_field_name("source")
        if source is not None:
            module = _string_literal_value(source, text)
            if module:
                self._add_import_node(
                    namespace,
                    rel,
                    file_id,
                    module,
                    source_ref,
                    nodes,
                    edges,
                )
        if declaration is not None:
            kind = _node_kind(declaration)
            if kind == "function_declaration":
                self._add_function_symbol(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    declaration,
                    text,
                    nodes,
                    edges,
                    exported=True,
                )
                return
            if kind == "class_declaration":
                self._add_class_symbol(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    declaration,
                    text,
                    nodes,
                    edges,
                    exported=True,
                )
                return
            if kind in {"lexical_declaration", "variable_declaration"}:
                self._add_exported_declarators(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    declaration,
                    text,
                    nodes,
                    edges,
                )
                return
            if _statement_starts_with(statement, text, "export default"):
                self._add_export_only(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    "default",
                    source_ref,
                    export_kind="default",
                    nodes=nodes,
                    edges=edges,
                )
                return
        for child in _node_named_children(statement):
            if _node_kind(child) in {"export_clause", "named_exports"}:
                self._add_named_exports(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    child,
                    text,
                    nodes,
                    edges,
                )

    def _add_exported_declarators(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        declaration: Any,
        text: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        for child in _node_named_children(declaration):
            if _node_kind(child) != "variable_declarator":
                continue
            name_node = child.child_by_field_name("name")
            if name_node is None:
                continue
            label = _node_text(name_node, text).strip()
            if not label:
                continue
            value_node = child.child_by_field_name("value")
            source_ref = _source_ref_from_node(rel, name_node)
            if value_node is not None and _node_kind(value_node) in {
                "arrow_function",
                "function",
                "function_expression",
            }:
                self._add_symbol(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    label,
                    NODE_SCRIPT_FUNCTION,
                    source_ref,
                    nodes,
                    edges,
                    exported=True,
                )
                continue
            if value_node is not None and _node_kind(value_node) in {
                "class",
                "class_declaration",
                "class_expression",
            }:
                self._add_symbol(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    label,
                    NODE_SCRIPT_CLASS,
                    source_ref,
                    nodes,
                    edges,
                    exported=True,
                )
                continue
            self._add_export_only(
                namespace,
                rel,
                file_id,
                module_id,
                label,
                source_ref,
                export_kind="direct",
                nodes=nodes,
                edges=edges,
            )

    def _add_named_exports(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        clause: Any,
        text: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        for child in _node_named_children(clause):
            if _node_kind(child) != "export_specifier":
                continue
            name_node = child.child_by_field_name("name")
            if name_node is None:
                name_node = child.child_by_field_name("alias")
            if name_node is None:
                continue
            label = _node_text(name_node, text).strip()
            if not label:
                continue
            self._add_export_only(
                namespace,
                rel,
                file_id,
                module_id,
                label,
                _source_ref_from_node(rel, name_node),
                export_kind="named",
                nodes=nodes,
                edges=edges,
            )

    def _add_function_symbol(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        declaration: Any,
        text: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
        *,
        exported: bool,
    ) -> None:
        name_node = declaration.child_by_field_name("name")
        if name_node is None:
            return
        label = _node_text(name_node, text).strip()
        if not label:
            return
        self._add_symbol(
            namespace,
            rel,
            file_id,
            module_id,
            label,
            NODE_SCRIPT_FUNCTION,
            _source_ref_from_node(rel, name_node),
            nodes,
            edges,
            exported=exported,
        )

    def _add_class_symbol(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        declaration: Any,
        text: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
        *,
        exported: bool,
    ) -> None:
        name_node = declaration.child_by_field_name("name")
        if name_node is None:
            return
        label = _node_text(name_node, text).strip()
        if not label:
            return
        self._add_symbol(
            namespace,
            rel,
            file_id,
            module_id,
            label,
            NODE_SCRIPT_CLASS,
            _source_ref_from_node(rel, name_node),
            nodes,
            edges,
            exported=exported,
        )

    def _add_symbol(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        label: str,
        kind: str,
        source_ref: SourceRef,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
        *,
        exported: bool,
    ) -> None:
        symbol_id = node_id(namespace, kind, f"{rel}:{label}")
        nodes[symbol_id] = GraphNode(
            id=symbol_id,
            kind=kind,
            label=label,
            source_ref=source_ref,
            text=label,
            metadata={
                "qualified_name": label,
                "module_id": module_id,
                "module_name": module_name(rel),
                "language": script_language(rel),
                "export_kind": "export" if exported else "local",
                "parser": self.name,
                "parser_version": self.version,
            },
        )
        edges[edge_id(namespace, file_id, EDGE_DEFINES, symbol_id)] = GraphEdge(
            id=edge_id(namespace, file_id, EDGE_DEFINES, symbol_id),
            kind=EDGE_DEFINES,
            source_id=file_id,
            target_id=symbol_id,
            source_ref=source_ref,
        )
        edges[edge_id(namespace, module_id, EDGE_PARENT_SYMBOL, symbol_id)] = GraphEdge(
            id=edge_id(namespace, module_id, EDGE_PARENT_SYMBOL, symbol_id),
            kind=EDGE_PARENT_SYMBOL,
            source_id=module_id,
            target_id=symbol_id,
            source_ref=source_ref,
        )
        if exported:
            export_id = node_id(namespace, NODE_SCRIPT_EXPORT, f"{rel}:export:{label}")
            nodes[export_id] = GraphNode(
                id=export_id,
                kind=NODE_SCRIPT_EXPORT,
                label=label,
                source_ref=source_ref,
                text=label,
                metadata={
                    "qualified_name": label,
                    "module_id": module_id,
                    "module_name": module_name(rel),
                    "language": script_language(rel),
                    "export_kind": "direct",
                    "parser": self.name,
                    "parser_version": self.version,
                },
            )
            edges[edge_id(namespace, symbol_id, EDGE_DEFINES, export_id)] = GraphEdge(
                id=edge_id(namespace, symbol_id, EDGE_DEFINES, export_id),
                kind=EDGE_DEFINES,
                source_id=symbol_id,
                target_id=export_id,
                source_ref=source_ref,
            )

    def _add_export_only(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        label: str,
        source_ref: SourceRef,
        *,
        export_kind: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        export_id = node_id(namespace, NODE_SCRIPT_EXPORT, f"{rel}:export:{label}")
        nodes[export_id] = GraphNode(
            id=export_id,
            kind=NODE_SCRIPT_EXPORT,
            label=label,
            source_ref=source_ref,
            text=label,
            metadata={
                "qualified_name": label,
                "module_id": module_id,
                "module_name": module_name(rel),
                "language": script_language(rel),
                "export_kind": export_kind,
                "parser": self.name,
                "parser_version": self.version,
            },
        )
        edges[edge_id(namespace, file_id, EDGE_DEFINES, export_id)] = GraphEdge(
            id=edge_id(namespace, file_id, EDGE_DEFINES, export_id),
            kind=EDGE_DEFINES,
            source_id=file_id,
            target_id=export_id,
            source_ref=source_ref,
        )

    def _add_import_node(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module: str,
        source_ref: SourceRef,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        import_id = node_id(namespace, NODE_IMPORT, f"import:{rel}:{module}")
        nodes[import_id] = GraphNode(
            id=import_id,
            kind=NODE_IMPORT,
            label=module,
            source_ref=source_ref,
            metadata={
                "external": not module.startswith((".", "/")),
                "language": script_language(rel),
                "source_path": rel,
                "parser": self.name,
                "parser_version": self.version,
            },
        )
        edges[edge_id(namespace, file_id, EDGE_IMPORTS, import_id)] = GraphEdge(
            id=edge_id(namespace, file_id, EDGE_IMPORTS, import_id),
            kind=EDGE_IMPORTS,
            source_id=file_id,
            target_id=import_id,
            source_ref=source_ref,
        )


def _tree_sitter_language(rel: str) -> str:
    return "typescript" if Path(rel).suffix.lower() in {".ts", ".tsx"} else "javascript"


def _tree_root_node(tree: Any) -> Any:
    root = tree.root_node
    return root() if callable(root) else root


def _parse_tree(parser: Any, text: str) -> Any:
    payload = text.encode("utf-8")
    try:
        return parser.parse(payload)
    except TypeError:
        return parser.parse(text)


def _node_kind(node: Any) -> str:
    kind = getattr(node, "kind", getattr(node, "type", ""))
    return str(kind() if callable(kind) else kind)


def _node_named_children(node: Any) -> tuple[Any, ...]:
    count = node.named_child_count
    count_value = int(count() if callable(count) else count)
    return tuple(node.named_child(index) for index in range(count_value))


def _node_has_error(node: Any) -> bool:
    has_error = node.has_error
    return bool(has_error() if callable(has_error) else has_error)


def _node_start_byte(node: Any) -> int:
    value = node.start_byte
    return int(value() if callable(value) else value)


def _node_end_byte(node: Any) -> int:
    value = node.end_byte
    return int(value() if callable(value) else value)


def _node_point_row(point: Any) -> int:
    return int(getattr(point, "row", 0))


def _node_point_column(point: Any) -> int:
    return int(getattr(point, "column", 0))


def _node_start_position(node: Any) -> Any:
    value = _node_attribute(node, "start_position", "start_point")
    return value() if callable(value) else value


def _node_end_position(node: Any) -> Any:
    value = _node_attribute(node, "end_position", "end_point")
    return value() if callable(value) else value


def _node_text(node: Any, text: str) -> str:
    raw = text.encode("utf-8")[_node_start_byte(node) : _node_end_byte(node)]
    return raw.decode("utf-8")


def _node_attribute(node: Any, *names: str) -> Any:
    for name in names:
        if hasattr(node, name):
            return getattr(node, name)
    raise AttributeError(f"node does not expose any of: {', '.join(names)}")


def _string_literal_value(node: Any, text: str) -> str:
    value = _node_text(node, text).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _source_ref_from_node(rel: str, node: Any) -> SourceRef:
    start = _node_start_position(node)
    end = _node_end_position(node)
    return SourceRef(
        path=rel,
        line=_node_point_row(start) + 1,
        column=_node_point_column(start),
        end_line=_node_point_row(end) + 1,
        end_column=_node_point_column(end),
    )


def _statement_starts_with(node: Any, text: str, prefix: str) -> bool:
    return _node_text(node, text).lstrip().startswith(prefix)


def _with_script_parser_metadata(
    node: GraphNode,
    *,
    parser_name: str,
    parser_version: str,
) -> GraphNode:
    if str(node.metadata.get("parser", "")) != ScriptLexicalParser.name:
        return node
    metadata = dict(node.metadata)
    metadata["parser"] = parser_name
    metadata["parser_version"] = parser_version
    return GraphNode(
        id=node.id,
        kind=node.kind,
        label=node.label,
        source_ref=node.source_ref,
        text=node.text,
        metadata=metadata,
    )


def build_optional_script_precise_parser() -> ScriptTreeSitterParser | None:
    try:
        from tree_sitter_language_pack import get_parser
    except ImportError:
        return None
    return ScriptTreeSitterParser(get_parser, fallback=ScriptLexicalParser())


__all__ = ["ScriptTreeSitterParser", "build_optional_script_precise_parser"]
