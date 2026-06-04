"""Reference stdio runner for the PragmaGraph local service surface."""

from __future__ import annotations

import json
import sys
from typing import TextIO

from pragmagraph.models import PragmaGraphError
from pragmagraph.service.constants import ERROR_INVALID_REQUEST
from pragmagraph.service.models import ServiceRequest, ServiceResponse
from pragmagraph.service.runtime import LocalQueryService


def request_from_json_line(line: str) -> ServiceRequest:
    """Parse one JSON request line."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise PragmaGraphError(
            "service request must be valid JSON",
            code=ERROR_INVALID_REQUEST,
            details={"line": exc.lineno, "column": exc.colno},
        ) from exc
    if not isinstance(payload, dict):
        raise PragmaGraphError(
            "service request JSON root must be an object",
            code=ERROR_INVALID_REQUEST,
        )
    return ServiceRequest.from_dict(payload)


def run_stdio_service(
    service: LocalQueryService,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run a newline-delimited JSON stdio service loop."""
    in_stream = stdin or sys.stdin
    out_stream = stdout or sys.stdout
    for raw_line in in_stream:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = request_from_json_line(line)
            response, should_shutdown = service.handle_request(request)
        except PragmaGraphError as exc:
            response = ServiceResponse.failure(
                "",
                code=str(exc.code),
                message=str(exc.message),
                details=exc.details,
            )
            should_shutdown = False
        out_stream.write(json.dumps(response.to_dict(), sort_keys=True) + "\n")
        out_stream.flush()
        if should_shutdown:
            break
    return 0


__all__ = ["request_from_json_line", "run_stdio_service"]
