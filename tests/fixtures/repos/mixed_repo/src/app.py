import json
import missing.module  # noqa: F401 - fixture intentionally records unresolved import.
from helper import make_value


class Base:
    pass


class RuntimeGraph(Base):
    def build(self) -> str:
        return json.dumps({"ok": make_value()})
