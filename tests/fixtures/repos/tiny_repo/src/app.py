import json


class RuntimeGraph:
    """Tiny fixture symbol for deterministic query tests."""


def build_runtime_graph() -> RuntimeGraph:
    json.dumps({"fixture": "runtime"})
    return RuntimeGraph()
