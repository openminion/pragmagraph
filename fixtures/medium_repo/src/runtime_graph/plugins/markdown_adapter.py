from runtime_graph.core.state import GraphState


class MarkdownAdapter:
    def render(self, summary: str) -> str:
        state = GraphState(root_path="docs")
        return f"# Runtime Graph\\n\\n{summary}\\n\\n{state.summary()}"
