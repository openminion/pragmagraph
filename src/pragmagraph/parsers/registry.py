"""Parser registry contracts and optional-family diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pragmagraph.models import ParserDiagnostic, ParserResult

PARSER_VERSION = "pragmagraph.parser.v1alpha1"
SCRIPT_PARSER_VERSION = "pragmagraph.script_lexical.v1alpha1"
SCRIPT_PRECISE_PARSER_VERSION = "pragmagraph.script_tree_sitter.v1alpha1"
SCRIPT_SUFFIXES = frozenset({".cjs", ".js", ".jsx", ".mjs", ".ts", ".tsx"})


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
    available: bool = False
    preferred_parser: str = ""
    fallback_parser: str = ""


@dataclass(frozen=True)
class ParserSelection:
    """One parser decision plus any typed fallback diagnostics."""

    parser: BuiltInParser | None
    diagnostics: tuple[ParserDiagnostic, ...] = ()


@dataclass(frozen=True)
class ParserRegistry:
    """Suffix-based parser registry."""

    parsers: tuple[BuiltInParser, ...]
    optional_families: tuple[OptionalParserFamily, ...] = ()

    def parser_for(self, path: str | Path) -> BuiltInParser | None:
        return self.select_parser(path).parser

    def select_parser(self, path: str | Path, *, rel: str = "") -> ParserSelection:
        suffix = Path(path).suffix.lower()
        selected: BuiltInParser | None = None
        for parser in self.parsers:
            if suffix in parser.suffixes:
                selected = parser
                break
        diagnostics: list[ParserDiagnostic] = []
        for family in self.optional_families:
            if suffix not in family.suffixes or family.available:
                continue
            if selected is None or (
                family.fallback_parser and selected.name == family.fallback_parser
            ):
                diagnostics.append(
                    ParserDiagnostic(
                        "optional_parser_unavailable",
                        "optional parser family is unavailable in the current environment",
                        rel,
                        details={
                            "parser_family": family.name,
                            "dependency": family.dependency,
                            "suffix": suffix,
                            "preferred_parser": family.preferred_parser,
                            "fallback_parser": family.fallback_parser,
                        },
                    )
                )
        return ParserSelection(parser=selected, diagnostics=tuple(diagnostics))

    def unavailable_parser_diagnostic(
        self, path: str | Path, *, rel: str
    ) -> ParserDiagnostic | None:
        selection = self.select_parser(path, rel=rel)
        return selection.diagnostics[0] if selection.diagnostics else None


__all__ = [
    "BuiltInParser",
    "OptionalParserFamily",
    "PARSER_VERSION",
    "ParserRegistry",
    "ParserSelection",
    "SCRIPT_PARSER_VERSION",
    "SCRIPT_PRECISE_PARSER_VERSION",
    "SCRIPT_SUFFIXES",
]
