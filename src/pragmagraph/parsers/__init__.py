"""Built-in parser registry for observed code facts."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

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
from pragmagraph.portability import edge_id, node_id
from pragmagraph.security import escape_label

PARSER_VERSION = "pragmagraph.parser.v1alpha1"
SCRIPT_PARSER_VERSION = "pragmagraph.script_lexical.v1alpha1"


class BuiltInParser(Protocol):
    """Parser contract for package-owned deterministic parsers."""

    name: str
    version: str
    suffixes: frozenset[str]

    def parse(
        self, *, namespace: str, rel: str, file_id: str, text: str
    ) -> ParserResult:
        """Parse one file and return observed graph facts."""


@dataclass(frozen=True)
class OptionalParserFamily:
    """Optional parser family declaration for known-but-unavailable suffixes."""

    name: str
    suffixes: frozenset[str]
    dependency: str = ""


@dataclass(frozen=True)
class ParserRegistry:
    """Suffix-based parser registry."""

    parsers: tuple[BuiltInParser, ...]
    optional_families: tuple[OptionalParserFamily, ...] = ()

    def parser_for(self, path: str | Path) -> BuiltInParser | None:
        suffix = Path(path).suffix.lower()
        for parser in self.parsers:
            if suffix in parser.suffixes:
                return parser
        return None

    def unavailable_parser_diagnostic(
        self, path: str | Path, *, rel: str
    ) -> ParserDiagnostic | None:
        suffix = Path(path).suffix.lower()
        for family in self.optional_families:
            if suffix in family.suffixes:
                return ParserDiagnostic(
                    "optional_parser_unavailable",
                    "optional parser family is unavailable in the current environment",
                    rel,
                    details={
                        "parser_family": family.name,
                        "dependency": family.dependency,
                        "suffix": suffix,
                    },
                )
        return None


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
    suffixes = frozenset({".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"})

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
    _CONST_EXPORT_RE = re.compile(
        r"""^\s*export\s+(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)""",
        re.MULTILINE,
    )
    _NAMED_EXPORT_RE = re.compile(r"""^\s*export\s*\{\s*([^}]+)\s*\}""", re.MULTILINE)

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
        const_match = self._CONST_EXPORT_RE.match(line)
        if const_match:
            symbol_defs.append((const_match.group(1), NODE_SCRIPT_EXPORT))
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
        source_ref = SourceRef(
            path=self.rel,
            line=getattr(node, "lineno", None),
            column=getattr(node, "col_offset", None),
            end_line=getattr(node, "end_lineno", None),
            end_column=getattr(node, "end_col_offset", None),
        )
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
            SourceRef(path=self.rel, line=getattr(node, "lineno", None)),
            {"symbol_type": symbol_type, "legacy_compat": True},
        )
        self._edge(self.file_id, EDGE_DEFINES, symbol_id, node)

    def _import(self, module: str, node: ast.AST) -> None:
        import_id = node_id(self.namespace, NODE_IMPORT, f"import:{module}")
        self._add_node(
            import_id,
            NODE_IMPORT,
            module,
            SourceRef(path=self.rel, line=getattr(node, "lineno", None)),
            {"external": True},
        )
        self._edge(self.file_id, EDGE_IMPORTS, import_id, node)
        legacy_id = node_id(self.namespace, NODE_PYTHON_SYMBOL, f"import:{module}")
        self._add_node(
            legacy_id,
            NODE_PYTHON_SYMBOL,
            module,
            SourceRef(path=self.rel, line=getattr(node, "lineno", None)),
            {"external": True, "symbol_type": "import", "legacy_compat": True},
        )
        self._edge(self.file_id, EDGE_IMPORTS, legacy_id, node)

    def _external_symbol(self, label: str, kind: str, node: ast.AST) -> str:
        target_id = node_id(self.namespace, kind, f"external:{label}")
        self._add_node(
            target_id,
            kind,
            label,
            SourceRef(path=self.rel, line=getattr(node, "lineno", None)),
            {"external": True},
        )
        return target_id

    def _edge(self, source_id: str, kind: str, target_id: str, node: ast.AST) -> None:
        edge = GraphEdge(
            id=edge_id(self.namespace, source_id, kind, target_id),
            kind=kind,
            source_id=source_id,
            target_id=target_id,
            source_ref=SourceRef(path=self.rel, line=getattr(node, "lineno", None)),
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


def _parse_named_exports(value: str) -> Iterable[str]:
    for item in value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        left = candidate.split(" as ", 1)[0].strip()
        if left:
            yield left


def get_default_registry() -> ParserRegistry:
    """Return the built-in parser registry."""
    return ParserRegistry(parsers=(PythonAstParser(), ScriptLexicalParser()))


__all__ = [
    "BuiltInParser",
    "OptionalParserFamily",
    "PARSER_VERSION",
    "ParserRegistry",
    "PythonAstParser",
    "SCRIPT_PARSER_VERSION",
    "ScriptLexicalParser",
    "get_default_registry",
]
