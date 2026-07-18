"""Grammar-aware identities for canonical SCIP symbol strings."""

from __future__ import annotations

from dataclasses import dataclass

from pragmagraph.models import PragmaGraphError

_SIMPLE_CHARACTERS = frozenset(
    "_+-$0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)
_DESCRIPTOR_SUFFIXES = frozenset("/#.:!")


@dataclass(frozen=True)
class ScipSymbolIdentity:
    """Parsed identity whose original SCIP spelling remains authoritative."""

    original: str
    scheme: str = ""
    package_manager: str = ""
    package_name: str = ""
    package_version: str = ""
    descriptors: tuple[str, ...] = ()
    local_id: str = ""

    @property
    def is_local(self) -> bool:
        return bool(self.local_id)

    @property
    def has_complete_package(self) -> bool:
        fields = (self.package_manager, self.package_name, self.package_version)
        return not self.is_local and all(field and field != "." for field in fields)

    @property
    def version_agnostic_key(self) -> tuple[str, str, str, tuple[str, ...]]:
        return (
            self.scheme,
            self.package_manager,
            self.package_name,
            self.descriptors,
        )

    def to_symbol(self) -> str:
        """Return the byte-for-byte producer-supplied canonical spelling."""
        return self.original


def parse_scip_symbol(value: str) -> ScipSymbolIdentity:
    """Parse and validate one canonical SCIP symbol string."""
    symbol = str(value or "")
    if symbol.startswith("local "):
        local_id = symbol[6:]
        if not local_id or any(char not in _SIMPLE_CHARACTERS for char in local_id):
            raise _invalid(symbol, "invalid local symbol identifier")
        return ScipSymbolIdentity(original=symbol, local_id=local_id)

    fields, descriptor_text = _split_global_fields(symbol)
    scheme, manager, package_name, version = fields
    if not scheme or scheme.startswith("local"):
        raise _invalid(symbol, "SCIP symbol scheme is invalid")
    descriptors = _parse_descriptors(symbol, descriptor_text)
    return ScipSymbolIdentity(
        original=symbol,
        scheme=scheme,
        package_manager=manager,
        package_name=package_name,
        package_version=version,
        descriptors=descriptors,
    )


def require_cross_repository_symbol(value: str) -> ScipSymbolIdentity:
    """Return a global, package-qualified SCIP identity or raise a typed error."""
    identity = parse_scip_symbol(value)
    if identity.is_local:
        raise _invalid(
            identity.original, "local SCIP symbols cannot cross repositories"
        )
    if not identity.has_complete_package:
        raise _invalid(
            identity.original,
            "cross-repository SCIP symbols require manager, package, and version",
        )
    return identity


def _split_global_fields(symbol: str) -> tuple[tuple[str, str, str, str], str]:
    fields: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(symbol) and len(fields) < 4:
        char = symbol[index]
        if char != " ":
            current.append(char)
            index += 1
            continue
        if index + 1 < len(symbol) and symbol[index + 1] == " ":
            current.append(" ")
            index += 2
            continue
        fields.append("".join(current))
        current = []
        index += 1
    if len(fields) != 4 or current or index >= len(symbol):
        raise _invalid(symbol, "global SCIP symbol requires four package fields")
    descriptor_text = symbol[index:]
    if not descriptor_text:
        raise _invalid(symbol, "global SCIP symbol requires at least one descriptor")
    return (fields[0], fields[1], fields[2], fields[3]), descriptor_text


def _parse_descriptors(symbol: str, text: str) -> tuple[str, ...]:
    descriptors: list[str] = []
    index = 0
    while index < len(text):
        start = index
        if text[index] == "[":
            index = _scan_group(symbol, text, index, "[", "]")
        elif text[index] == "(":
            index = _scan_group(symbol, text, index, "(", ")")
        else:
            index = _scan_identifier(symbol, text, index)
            if index < len(text) and text[index] == "(":
                index = _scan_method(symbol, text, index)
            elif index < len(text) and text[index] in _DESCRIPTOR_SUFFIXES:
                index += 1
            else:
                raise _invalid(symbol, "SCIP descriptor suffix is missing")
        descriptors.append(text[start:index])
    if not descriptors:
        raise _invalid(symbol, "global SCIP symbol requires descriptors")
    return tuple(descriptors)


def _scan_identifier(symbol: str, text: str, index: int) -> int:
    if index >= len(text):
        raise _invalid(symbol, "SCIP descriptor identifier is missing")
    if text[index] != "`":
        start = index
        while index < len(text) and text[index] in _SIMPLE_CHARACTERS:
            index += 1
        if index == start:
            raise _invalid(symbol, "SCIP descriptor identifier is invalid")
        return index

    index += 1
    content: list[str] = []
    while index < len(text):
        if text[index] != "`":
            content.append(text[index])
            index += 1
            continue
        if index + 1 < len(text) and text[index + 1] == "`":
            content.append("`")
            index += 2
            continue
        index += 1
        if not content or all(char in _SIMPLE_CHARACTERS for char in content):
            raise _invalid(symbol, "escaped SCIP identifier must require escaping")
        return index
    raise _invalid(symbol, "unterminated escaped SCIP identifier")


def _scan_group(
    symbol: str,
    text: str,
    index: int,
    opening: str,
    closing: str,
) -> int:
    if text[index] != opening:
        raise _invalid(symbol, "SCIP descriptor group is invalid")
    index += 1
    index = _scan_identifier(symbol, text, index)
    if index >= len(text) or text[index] != closing:
        raise _invalid(symbol, "SCIP descriptor group is unterminated")
    return index + 1


def _scan_method(symbol: str, text: str, index: int) -> int:
    index += 1
    start = index
    while index < len(text) and text[index] in _SIMPLE_CHARACTERS:
        index += 1
    if index < len(text) and text[index] == ")":
        index += 1
        if index < len(text) and text[index] == ".":
            return index + 1
    if index == start:
        raise _invalid(symbol, "SCIP method descriptor is malformed")
    raise _invalid(symbol, "SCIP method descriptor is unterminated")


def _invalid(symbol: str, message: str) -> PragmaGraphError:
    return PragmaGraphError(
        message,
        code="INVALID_SCIP_SYMBOL",
        details={"symbol": symbol},
    )


__all__ = [
    "ScipSymbolIdentity",
    "parse_scip_symbol",
    "require_cross_repository_symbol",
]
