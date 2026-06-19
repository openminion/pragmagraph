"""Internal immutable-coercion helpers shared by package DTO modules."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


def frozen_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


def tuple_str(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        text = str(value).strip()
        return (text,) if text else ()
    return tuple(str(item) for item in value)  # type: ignore[arg-type]
