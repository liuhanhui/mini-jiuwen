from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ModelTurn:
    text: str | None = None
    tool_calls: list[ToolCall] | None = None


@dataclass
class Token:
    text: str


class ScriptedModel:
    """Deterministic stand-in for an LLM. Used by tests and ``mini-swarm --demo``."""

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns)

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
        del messages, tools
        if not self._turns:
            raise RuntimeError("scripted model has no remaining turns")
        return self._turns.pop(0)

    def stream(self, messages: list[dict], tools: list[dict]):
        turn = self.complete(messages, tools)
        if turn.text and not turn.tool_calls:
            yield Token(turn.text)
        yield turn

    def remaining(self) -> int:
        return len(self._turns)
