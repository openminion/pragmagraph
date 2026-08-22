"""Shared CLI helpers for the PragmaGraph entrypoint."""

import json

from pragmagraph.cli.commands import (
    add_git_identity_mode_argument,
    add_json_flag,
    register_core_commands,
)


def print_payload(payload: object, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, sort_keys=True))
        return
    print(payload)


__all__ = [
    "add_git_identity_mode_argument",
    "add_json_flag",
    "print_payload",
    "register_core_commands",
]
