"""Built-in parser registry for observed code facts."""

from __future__ import annotations

from pragmagraph.parsers.python_ast import PythonAstParser
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
from pragmagraph.parsers.script import ScriptLexicalParser
from pragmagraph.parsers.script_precise import (
    ScriptTreeSitterParser,
    build_optional_script_precise_parser,
)


def get_default_registry() -> ParserRegistry:
    """Return the built-in parser registry."""
    script_lexical = ScriptLexicalParser()
    script_precise = build_optional_script_precise_parser()
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
