from runtime_graph.core.loader import SnapshotLoader
from runtime_graph.core.runtime import RuntimeGraph
from runtime_graph.plugins.markdown_adapter import MarkdownAdapter


def build_runtime() -> RuntimeGraph:
    loader = SnapshotLoader()
    adapter = MarkdownAdapter()
    return RuntimeGraph(loader=loader, adapter=adapter)
