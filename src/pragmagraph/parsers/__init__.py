"""Built-in parser registry for observed code facts."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Iterable

from pragmagraph.contracts import (
    EDGE_CALLS,
    EDGE_DEFINES,
    EDGE_IMPORTS,
    EDGE_INHERITS,
    EDGE_PARENT_SYMBOL,
    NODE_IMPORT,
    NODE_PYTHON_CLASS,
    NODE_PYTHON_FUNCTION,
    NODE_PYTHON_METHOD,
    NODE_PYTHON_MODULE,
    NODE_PYTHON_SYMBOL,
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
from pragmagraph.parsers.registry import (
    BuiltInParser,
    OptionalParserFamily,
    PARSER_VERSION,
    SCRIPT_PARSER_VERSION,
    SCRIPT_PRECISE_PARSER_VERSION,
    SCRIPT_SUFFIXES,
    ParserRegistry,
    ParserSelection,
)
from pragmagraph.portability import edge_id, node_id
from pragmagraph.security import escape_label


class PythonAstParser:
    """Deterministic Python AST parser."""

    name = "python_ast"
    version = PARSER_VERSION
    suffixes = frozenset({".py"})

    def parse(
        self, *, namespace: str, rel: str, file_id: str, text: str
    ) -> ParserResult:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            return ParserResult(
                diagnostics=(
                    ParserDiagnostic(
                        "python_syntax_error",
                        exc.msg,
                        rel,
                        line=exc.lineno,
                    ),
                )
            )

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        module_id = node_id(namespace, NODE_PYTHON_MODULE, rel)
        self._add_node(
            nodes,
            GraphNode(
                id=module_id,
                kind=NODE_PYTHON_MODULE,
                label=Path(rel).stem,
                source_ref=SourceRef(path=rel, line=1),
                metadata={
                    "module_name": _module_name(rel),
                    "parser": self.name,
                    "parser_version": self.version,
                },
            ),
        )
        self._add_edge(
            edges,
            GraphEdge(
                id=edge_id(namespace, file_id, EDGE_DEFINES, module_id),
                kind=EDGE_DEFINES,
                source_id=file_id,
                target_id=module_id,
                source_ref=SourceRef(path=rel, line=1),
            ),
        )
        visitor = _PythonFactVisitor(namespace, rel, file_id, module_id, nodes, edges)
        visitor.visit(tree)
        return ParserResult(
            nodes=tuple(sorted(nodes.values(), key=lambda node: node.id)),
            edges=tuple(sorted(edges.values(), key=lambda edge: edge.id)),
        )

    @staticmethod
    def _add_node(nodes: dict[str, GraphNode], node: GraphNode) -> None:
        nodes.setdefault(node.id, node)

    @staticmethod
    def _add_edge(edges: dict[str, GraphEdge], edge: GraphEdge) -> None:
        edges.setdefault(edge.id, edge)


class ScriptLexicalParser:
    """Deterministic lexical parser for JS/TS module structure."""

    name = "script_lexical"
    version = SCRIPT_PARSER_VERSION
    suffixes = SCRIPT_SUFFIXES

    _IMPORT_FROM_RE = re.compile(
        r"""^\s*import\s+(?:type\s+)?(?:.+?\s+from\s+)?["']([^"']+)["']""",
        re.MULTILINE,
    )
    _REQUIRE_RE = re.compile(r"""require\(\s*["']([^"']+)["']\s*\)""")
    _CLASS_RE = re.compile(
        r"""^\s*(?:export\s+default\s+|export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)""",
        re.MULTILINE,
    )
    _FUNCTION_RE = re.compile(
        r"""^\s*(?:export\s+default\s+|export\s+)?(?:async\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)""",
        re.MULTILINE,
    )
    _ARROW_FUNCTION_RE = re.compile(
        r"""^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][A-Za-z0-9_$]*)\s*=>""",
        re.MULTILINE,
    )
    _CONST_EXPORT_RE = re.compile(
        r"""^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)""",
        re.MULTILINE,
    )
    _TYPE_EXPORT_RE = re.compile(
        r"""^\s*export\s+(?:interface|type)\s+([A-Za-z_$][A-Za-z0-9_$]*)""",
        re.MULTILINE,
    )
    _NAMED_EXPORT_RE = re.compile(
        r"""^\s*export\s*\{\s*([^}]+?)\s*\}(?:\s+from\s+["'][^"']+["'])?""",
        re.MULTILINE,
    )

    def parse(
        self, *, namespace: str, rel: str, file_id: str, text: str
    ) -> ParserResult:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        module_id = node_id(namespace, NODE_SCRIPT_MODULE, rel)
        module_name = _module_name(rel)
        self._add_node(
            nodes,
            GraphNode(
                id=module_id,
                kind=NODE_SCRIPT_MODULE,
                label=Path(rel).stem,
                source_ref=SourceRef(path=rel, line=1),
                metadata={
                    "module_name": module_name,
                    "language": _script_language(rel),
                    "parser": self.name,
                    "parser_version": self.version,
                },
            ),
        )
        self._add_edge(
            edges,
            GraphEdge(
                id=edge_id(namespace, file_id, EDGE_DEFINES, module_id),
                kind=EDGE_DEFINES,
                source_id=file_id,
                target_id=module_id,
                source_ref=SourceRef(path=rel, line=1),
            ),
        )
        for line_number, line in enumerate(text.splitlines(), start=1):
            self._parse_imports(
                namespace, rel, file_id, line, line_number, nodes, edges
            )
            self._parse_symbols(
                namespace, rel, file_id, module_id, line, line_number, nodes, edges
            )
        return ParserResult(
            nodes=tuple(sorted(nodes.values(), key=lambda node: node.id)),
            edges=tuple(sorted(edges.values(), key=lambda edge: edge.id)),
        )

    def _parse_imports(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        line: str,
        line_number: int,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        for pattern in (self._IMPORT_FROM_RE, self._REQUIRE_RE):
            for match in pattern.finditer(line):
                module = match.group(1).strip()
                import_id = node_id(namespace, NODE_IMPORT, f"import:{rel}:{module}")
                source_ref = SourceRef(path=rel, line=line_number)
                self._add_node(
                    nodes,
                    GraphNode(
                        id=import_id,
                        kind=NODE_IMPORT,
                        label=module,
                        source_ref=source_ref,
                        metadata={
                            "external": not module.startswith((".", "/")),
                            "language": _script_language(rel),
                            "source_path": rel,
                            "parser": self.name,
                            "parser_version": self.version,
                        },
                    ),
                )
                self._add_edge(
                    edges,
                    GraphEdge(
                        id=edge_id(namespace, file_id, EDGE_IMPORTS, import_id),
                        kind=EDGE_IMPORTS,
                        source_id=file_id,
                        target_id=import_id,
                        source_ref=source_ref,
                    ),
                )

    def _parse_symbols(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        line: str,
        line_number: int,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        source_ref = SourceRef(path=rel, line=line_number)
        symbol_defs: list[tuple[str, str]] = []
        class_match = self._CLASS_RE.match(line)
        if class_match:
            symbol_defs.append((class_match.group(1), NODE_SCRIPT_CLASS))
        function_match = self._FUNCTION_RE.match(line)
        if function_match:
            symbol_defs.append((function_match.group(1), NODE_SCRIPT_FUNCTION))
        arrow_function_match = self._ARROW_FUNCTION_RE.match(line)
        if arrow_function_match:
            symbol_defs.append((arrow_function_match.group(1), NODE_SCRIPT_FUNCTION))
        const_match = self._CONST_EXPORT_RE.match(line)
        if const_match and not arrow_function_match:
            symbol_defs.append((const_match.group(1), NODE_SCRIPT_EXPORT))
        type_match = self._TYPE_EXPORT_RE.match(line)
        if type_match:
            symbol_defs.append((type_match.group(1), NODE_SCRIPT_EXPORT))
        for label, kind in symbol_defs:
            symbol_id = node_id(namespace, kind, f"{rel}:{label}")
            export_kind = "export" if line.lstrip().startswith("export") else "local"
            self._add_node(
                nodes,
                GraphNode(
                    id=symbol_id,
                    kind=kind,
                    label=label,
                    source_ref=source_ref,
                    text=label,
                    metadata={
                        "qualified_name": label,
                        "module_id": module_id,
                        "module_name": _module_name(rel),
                        "language": _script_language(rel),
                        "export_kind": export_kind,
                        "parser": self.name,
                        "parser_version": self.version,
                    },
                ),
            )
            self._add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, file_id, EDGE_DEFINES, symbol_id),
                    kind=EDGE_DEFINES,
                    source_id=file_id,
                    target_id=symbol_id,
                    source_ref=source_ref,
                ),
            )
            self._add_edge(
                edges,
                GraphEdge(
                    id=edge_id(namespace, module_id, EDGE_PARENT_SYMBOL, symbol_id),
                    kind=EDGE_PARENT_SYMBOL,
                    source_id=module_id,
                    target_id=symbol_id,
                    source_ref=source_ref,
                ),
            )
            if export_kind == "export":
                export_id = node_id(
                    namespace, NODE_SCRIPT_EXPORT, f"{rel}:export:{label}"
                )
                self._add_node(
                    nodes,
                    GraphNode(
                        id=export_id,
                        kind=NODE_SCRIPT_EXPORT,
                        label=label,
                        source_ref=source_ref,
                        text=label,
                        metadata={
                            "qualified_name": label,
                            "module_id": module_id,
                            "module_name": _module_name(rel),
                            "language": _script_language(rel),
                            "export_kind": "direct",
                            "parser": self.name,
                            "parser_version": self.version,
                        },
                    ),
                )
                self._add_edge(
                    edges,
                    GraphEdge(
                        id=edge_id(namespace, symbol_id, EDGE_DEFINES, export_id),
                        kind=EDGE_DEFINES,
                        source_id=symbol_id,
                        target_id=export_id,
                        source_ref=source_ref,
                    ),
                )
        named_export_match = self._NAMED_EXPORT_RE.match(line)
        if named_export_match:
            for item in _parse_named_exports(named_export_match.group(1)):
                export_id = node_id(
                    namespace, NODE_SCRIPT_EXPORT, f"{rel}:export:{item}"
                )
                self._add_node(
                    nodes,
                    GraphNode(
                        id=export_id,
                        kind=NODE_SCRIPT_EXPORT,
                        label=item,
                        source_ref=source_ref,
                        text=item,
                        metadata={
                            "qualified_name": item,
                            "module_id": module_id,
                            "module_name": _module_name(rel),
                            "language": _script_language(rel),
                            "export_kind": "named",
                            "parser": self.name,
                            "parser_version": self.version,
                        },
                    ),
                )
                self._add_edge(
                    edges,
                    GraphEdge(
                        id=edge_id(namespace, file_id, EDGE_DEFINES, export_id),
                        kind=EDGE_DEFINES,
                        source_id=file_id,
                        target_id=export_id,
                        source_ref=source_ref,
                    ),
                )

    @staticmethod
    def _add_node(nodes: dict[str, GraphNode], node: GraphNode) -> None:
        nodes.setdefault(node.id, node)

    @staticmethod
    def _add_edge(edges: dict[str, GraphEdge], edge: GraphEdge) -> None:
        edges.setdefault(edge.id, edge)


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
        except Exception as exc:
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
                "module_name": _module_name(rel),
                "language": _script_language(rel),
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
                    "module_name": _module_name(rel),
                    "language": _script_language(rel),
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
                "module_name": _module_name(rel),
                "language": _script_language(rel),
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
                "language": _script_language(rel),
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


class _PythonFactVisitor(ast.NodeVisitor):
    def __init__(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        self.namespace = namespace
        self.rel = rel
        self.file_id = file_id
        self.module_id = module_id
        self.nodes = nodes
        self.edges = edges
        self.parents: list[tuple[str, str]] = [(module_id, "module")]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        symbol_id = self._symbol(node.name, NODE_PYTHON_CLASS, node)
        self._legacy_symbol(node.name, "ClassDef", node)
        for base in node.bases:
            base_name = _expr_name(base)
            if base_name:
                base_id = self._external_symbol(base_name, NODE_PYTHON_CLASS, node)
                self._edge(symbol_id, EDGE_INHERITS, base_id, node)
        self.parents.append((symbol_id, "class"))
        self.generic_visit(node)
        self.parents.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function(node, is_async=True)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            self._import(alias.name, node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module:
            self._import(node.module, node)

    def _function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        *,
        is_async: bool = False,
    ) -> None:
        kind = (
            NODE_PYTHON_METHOD
            if self.parents[-1][1] == "class"
            else NODE_PYTHON_FUNCTION
        )
        symbol_id = self._symbol(node.name, kind, node, extra={"is_async": is_async})
        self._legacy_symbol(node.name, type(node).__name__, node)
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = _expr_name(child.func)
                if call_name:
                    target_id = self._external_symbol(
                        call_name, NODE_PYTHON_FUNCTION, child
                    )
                    self._edge(symbol_id, EDGE_CALLS, target_id, child)
        self.parents.append((symbol_id, "function"))
        self.generic_visit(node)
        self.parents.pop()

    def _symbol(
        self,
        label: str,
        kind: str,
        node: ast.AST,
        *,
        extra: dict[str, object] | None = None,
    ) -> str:
        parent_id, parent_kind = self.parents[-1]
        qualified = ".".join([*self._parent_labels(), label])
        symbol_id = node_id(self.namespace, kind, f"{self.rel}:{qualified}")
        source_ref = self._source_ref(node)
        metadata = {
            "qualified_name": qualified,
            "parent_id": parent_id,
            "parent_kind": parent_kind,
            "parser": "python_ast",
            **(extra or {}),
        }
        self._add_node(symbol_id, kind, label, source_ref, metadata)
        self._edge(parent_id, EDGE_PARENT_SYMBOL, symbol_id, node)
        if parent_id == self.module_id:
            self._edge(self.file_id, EDGE_DEFINES, symbol_id, node)
        return symbol_id

    def _legacy_symbol(self, label: str, symbol_type: str, node: ast.AST) -> None:
        symbol_id = node_id(self.namespace, NODE_PYTHON_SYMBOL, f"{self.rel}:{label}")
        self._add_node(
            symbol_id,
            NODE_PYTHON_SYMBOL,
            label,
            self._line_source_ref(node),
            {"symbol_type": symbol_type, "legacy_compat": True},
        )
        self._edge(self.file_id, EDGE_DEFINES, symbol_id, node)

    def _import(self, module: str, node: ast.AST) -> None:
        import_id = node_id(self.namespace, NODE_IMPORT, f"import:{module}")
        self._add_node(
            import_id,
            NODE_IMPORT,
            module,
            self._line_source_ref(node),
            {"external": True},
        )
        self._edge(self.file_id, EDGE_IMPORTS, import_id, node)
        legacy_id = node_id(self.namespace, NODE_PYTHON_SYMBOL, f"import:{module}")
        self._add_node(
            legacy_id,
            NODE_PYTHON_SYMBOL,
            module,
            self._line_source_ref(node),
            {"external": True, "symbol_type": "import", "legacy_compat": True},
        )
        self._edge(self.file_id, EDGE_IMPORTS, legacy_id, node)

    def _external_symbol(self, label: str, kind: str, node: ast.AST) -> str:
        target_id = node_id(self.namespace, kind, f"external:{label}")
        self._add_node(
            target_id,
            kind,
            label,
            self._line_source_ref(node),
            {"external": True},
        )
        return target_id

    def _edge(self, source_id: str, kind: str, target_id: str, node: ast.AST) -> None:
        edge = GraphEdge(
            id=edge_id(self.namespace, source_id, kind, target_id),
            kind=kind,
            source_id=source_id,
            target_id=target_id,
            source_ref=self._line_source_ref(node),
        )
        self.edges.setdefault(edge.id, edge)

    def _add_node(
        self,
        symbol_id: str,
        kind: str,
        label: str,
        source_ref: SourceRef,
        metadata: dict[str, object],
    ) -> None:
        self.nodes.setdefault(
            symbol_id,
            GraphNode(
                id=symbol_id,
                kind=kind,
                label=escape_label(label),
                source_ref=source_ref,
                text=escape_label(label),
                metadata=metadata,
            ),
        )

    def _line_source_ref(self, node: ast.AST) -> SourceRef:
        return SourceRef(path=self.rel, line=getattr(node, "lineno", None))

    def _source_ref(self, node: ast.AST) -> SourceRef:
        return SourceRef(
            path=self.rel,
            line=getattr(node, "lineno", None),
            column=getattr(node, "col_offset", None),
            end_line=getattr(node, "end_lineno", None),
            end_column=getattr(node, "end_col_offset", None),
        )

    def _parent_labels(self) -> list[str]:
        labels: list[str] = []
        for parent_id, kind in self.parents[1:]:
            if kind == "module":
                continue
            labels.append(parent_id.rsplit(":", 1)[-1].split(".")[-1])
        return labels


def _expr_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _expr_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return _expr_name(node.func)
    return ""


def _module_name(rel: str) -> str:
    path = Path(rel)
    parts = list(path.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or path.stem


def _script_language(rel: str) -> str:
    suffix = Path(rel).suffix.lower()
    return "typescript" if suffix in {".ts", ".tsx"} else "javascript"


def _tree_sitter_language(rel: str) -> str:
    return "typescript" if Path(rel).suffix.lower() in {".ts", ".tsx"} else "javascript"


def _parse_named_exports(value: str) -> Iterable[str]:
    for item in value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        left = candidate.split(" as ", 1)[0].strip()
        if left:
            yield left


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


def _build_optional_script_precise_parser() -> ScriptTreeSitterParser | None:
    try:
        from tree_sitter_language_pack import get_parser
    except ImportError:
        return None
    return ScriptTreeSitterParser(get_parser, fallback=ScriptLexicalParser())


def get_default_registry() -> ParserRegistry:
    """Return the built-in parser registry."""
    script_lexical = ScriptLexicalParser()
    script_precise = _build_optional_script_precise_parser()
    parsers: list[BuiltInParser] = [PythonAstParser()]
    if script_precise is not None:
        parsers.append(script_precise)
    parsers.append(script_lexical)
    return ParserRegistry(
        parsers=tuple(parsers),
        optional_families=(
            OptionalParserFamily(
                name="tree_sitter_script_precise",
                suffixes=SCRIPT_SUFFIXES,
                dependency="pragmagraph[precise]",
                available=script_precise is not None,
                preferred_parser="script_tree_sitter",
                fallback_parser="script_lexical",
            ),
        ),
    )


__all__ = [
    "BuiltInParser",
    "OptionalParserFamily",
    "PARSER_VERSION",
    "ParserSelection",
    "ParserRegistry",
    "PythonAstParser",
    "SCRIPT_PRECISE_PARSER_VERSION",
    "SCRIPT_PARSER_VERSION",
    "ScriptLexicalParser",
    "ScriptTreeSitterParser",
    "get_default_registry",
]
