from pathlib import Path

from runtime_graph.core.state import GraphState


class SnapshotLoader:
    def load(self, root: str) -> GraphState:
        return GraphState(root_path=str(Path(root)))
