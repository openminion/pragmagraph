from runtime_graph.core.contracts import SnapshotContract
from runtime_graph.core.loader import SnapshotLoader
from runtime_graph.plugins.markdown_adapter import MarkdownAdapter


class RuntimeGraph(SnapshotContract):
    def __init__(self, *, loader: SnapshotLoader, adapter: MarkdownAdapter) -> None:
        self.loader = loader
        self.adapter = adapter

    def render(self, root: str) -> str:
        state = self.loader.load(root)
        return self.adapter.render(state.summary())
