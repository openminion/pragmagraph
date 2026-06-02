class GraphState:
    def __init__(self, *, root_path: str) -> None:
        self.root_path = root_path

    def summary(self) -> str:
        return f"GraphState({self.root_path})"
