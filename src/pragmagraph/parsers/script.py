"""Lexical JavaScript and TypeScript parser for observed script facts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

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
from pragmagraph.models import GraphEdge, GraphNode, ParserResult, SourceRef
from pragmagraph.parsers.common import module_name, script_language
from pragmagraph.parsers.registry import SCRIPT_PARSER_VERSION, SCRIPT_SUFFIXES
from pragmagraph.portability import edge_id, node_id


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
        module_label = module_name(rel)
        self._add_node(
            nodes,
            GraphNode(
                id=module_id,
                kind=NODE_SCRIPT_MODULE,
                label=Path(rel).stem,
                source_ref=SourceRef(path=rel, line=1),
                metadata={
                    "module_name": module_label,
                    "language": script_language(rel),
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
                            "language": script_language(rel),
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
        for label, kind in self._symbol_definitions(line):
            self._add_symbol_definition(
                namespace,
                rel,
                file_id,
                module_id,
                line,
                label,
                kind,
                source_ref,
                nodes,
                edges,
            )
        named_export_match = self._NAMED_EXPORT_RE.match(line)
        if named_export_match:
            for item in _parse_named_exports(named_export_match.group(1)):
                self._add_named_export(
                    namespace,
                    rel,
                    file_id,
                    module_id,
                    item,
                    source_ref,
                    nodes,
                    edges,
                )

    def _symbol_definitions(self, line: str) -> list[tuple[str, str]]:
        definitions: list[tuple[str, str]] = []
        class_match = self._CLASS_RE.match(line)
        if class_match:
            definitions.append((class_match.group(1), NODE_SCRIPT_CLASS))
        function_match = self._FUNCTION_RE.match(line)
        if function_match:
            definitions.append((function_match.group(1), NODE_SCRIPT_FUNCTION))
        arrow_function_match = self._ARROW_FUNCTION_RE.match(line)
        if arrow_function_match:
            definitions.append((arrow_function_match.group(1), NODE_SCRIPT_FUNCTION))
        const_match = self._CONST_EXPORT_RE.match(line)
        if const_match and not arrow_function_match:
            definitions.append((const_match.group(1), NODE_SCRIPT_EXPORT))
        type_match = self._TYPE_EXPORT_RE.match(line)
        if type_match:
            definitions.append((type_match.group(1), NODE_SCRIPT_EXPORT))
        return definitions

    def _add_symbol_definition(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        line: str,
        label: str,
        kind: str,
        source_ref: SourceRef,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
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
                    "module_name": module_name(rel),
                    "language": script_language(rel),
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
            self._add_direct_export(
                namespace, rel, symbol_id, module_id, label, source_ref, nodes, edges
            )

    def _add_direct_export(
        self,
        namespace: str,
        rel: str,
        symbol_id: str,
        module_id: str,
        label: str,
        source_ref: SourceRef,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        export_id = node_id(namespace, NODE_SCRIPT_EXPORT, f"{rel}:export:{label}")
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
                    "module_name": module_name(rel),
                    "language": script_language(rel),
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

    def _add_named_export(
        self,
        namespace: str,
        rel: str,
        file_id: str,
        module_id: str,
        label: str,
        source_ref: SourceRef,
        nodes: dict[str, GraphNode],
        edges: dict[str, GraphEdge],
    ) -> None:
        export_id = node_id(namespace, NODE_SCRIPT_EXPORT, f"{rel}:export:{label}")
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
                    "module_name": module_name(rel),
                    "language": script_language(rel),
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


def _parse_named_exports(value: str) -> Iterable[str]:
    for item in value.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        left = candidate.split(" as ", 1)[0].strip()
        if left:
            yield left


__all__ = ["ScriptLexicalParser"]
