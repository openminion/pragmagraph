"""Python AST parser for observed code facts."""

from __future__ import annotations

import ast
from pathlib import Path

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
)
from pragmagraph.models import (
    GraphEdge,
    GraphNode,
    ParserDiagnostic,
    ParserResult,
    SourceRef,
)
from pragmagraph.parsers.common import module_name
from pragmagraph.parsers.registry import PARSER_VERSION
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
                    "module_name": module_name(rel),
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


__all__ = ["PythonAstParser"]
