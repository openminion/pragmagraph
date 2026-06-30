"""Parser-family support matrix for public package consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pragmagraph.parsers import SCRIPT_SUFFIXES, get_default_registry


@dataclass(frozen=True)
class ParserFamilySupport:
    """One parser-family support fact."""

    family: str
    suffixes: tuple[str, ...]
    status: str
    parser: str = ""
    dependency: str = ""
    fallback_parser: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "suffixes": list(self.suffixes),
            "status": self.status,
            "parser": self.parser,
            "dependency": self.dependency,
            "fallback_parser": self.fallback_parser,
        }


def build_parser_support_matrix() -> tuple[ParserFamilySupport, ...]:
    """Return deterministic parser-family support declarations."""
    registry = get_default_registry()
    built_in = {
        parser.name: tuple(sorted(parser.suffixes)) for parser in registry.parsers
    }
    rows = [
        ParserFamilySupport(
            family="python_ast",
            suffixes=built_in.get("python_ast", (".py",)),
            status="built_in",
            parser="python_ast",
        ),
        ParserFamilySupport(
            family="script_lexical",
            suffixes=built_in.get("script_lexical", tuple(sorted(SCRIPT_SUFFIXES))),
            status="built_in",
            parser="script_lexical",
        ),
    ]
    for family in registry.optional_families:
        rows.append(
            ParserFamilySupport(
                family=family.name,
                suffixes=tuple(sorted(family.suffixes)),
                status="available" if family.available else "optional_unavailable",
                parser=family.preferred_parser,
                dependency=family.dependency,
                fallback_parser=family.fallback_parser,
            )
        )
    return tuple(sorted(rows, key=lambda item: item.family))


__all__ = ["ParserFamilySupport", "build_parser_support_matrix"]
