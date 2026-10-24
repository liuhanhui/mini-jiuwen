from __future__ import annotations

from pathlib import Path

MEMORY_FILES = ("AGENTS.md", "MEMORY.md")


def load_memory_messages(workspace: Path) -> list[dict]:
    messages: list[dict] = []
    root = Path(workspace)
    for name in MEMORY_FILES:
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig").strip()
        if not text:
            continue
        messages.append({"role": "system", "content": f"# {name}\n{text}"})
    return messages


def messages_with_memory(workspace: Path, messages: list[dict]) -> list[dict]:
    return load_memory_messages(workspace) + list(messages)
