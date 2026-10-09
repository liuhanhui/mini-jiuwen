from __future__ import annotations

import json
from pathlib import Path


class Session:
    def __init__(self, session_id: str, store_dir: Path) -> None:
        self.session_id = session_id
        self.store_dir = Path(store_dir)
        self.messages: list[dict] = []

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str, tool_calls: list[dict] | None = None) -> None:
        message: dict = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.messages.append(message)

    def add_tool(self, call_id: str, output: str) -> None:
        self.messages.append(
            {"role": "tool", "tool_call_id": call_id, "content": output}
        )

    def save(self) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        path = self.store_dir / f"{self.session_id}.json"
        path.write_text(
            json.dumps({"messages": self.messages}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, session_id: str, store_dir: Path) -> Session:
        path = Path(store_dir) / f"{session_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        session = cls(session_id=session_id, store_dir=store_dir)
        session.messages = list(data.get("messages") or [])
        return session
