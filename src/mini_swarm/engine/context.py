from __future__ import annotations

from pathlib import Path

from mini_swarm.engine.memory import load_memory_messages
from mini_swarm.engine.skills import load_skill_catalog_messages


def messages_for_complete(workspace: Path, messages: list[dict]) -> list[dict]:
    return (
        load_memory_messages(workspace)
        + load_skill_catalog_messages(workspace)
        + list(messages)
    )
