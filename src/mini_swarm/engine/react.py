from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from mini_swarm.engine.model import ModelTurn, ToolCall
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import ToolError, ToolRegistry


class Model(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn: ...


@dataclass
class Event:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    final_text: str | None
    events: list[Event]
    stopped_by: str


class ReactAgent:
    """Harness inner loop: Think → Act → Observe. The only while that calls the model."""

    def __init__(
        self,
        model: Model,
        tools: ToolRegistry,
        session: Session,
        stop: StopPolicy | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.session = session
        self.stop = stop or StopPolicy()

    def run(self, query: str) -> RunResult:
        self.session.add_user(query)
        events: list[Event] = []
        step = 0
        final_text: str | None = None
        stopped_by = "max_steps"

        while not self.stop.should_stop(step=step, has_final_text=False):
            turn = self.model.complete(self.session.messages, self.tools.schemas())
            step += 1

            if turn.tool_calls:
                self._apply_tool_turn(turn.tool_calls, events)
                continue

            final_text = turn.text or ""
            self.session.add_assistant(final_text)
            events.append(Event(kind="text.delta", payload={"text": final_text}))
            events.append(Event(kind="turn.complete", payload={}))
            stopped_by = "final_text"
            break

        self.session.save()
        return RunResult(final_text=final_text, events=events, stopped_by=stopped_by)

    def _apply_tool_turn(self, calls: list[ToolCall], events: list[Event]) -> None:
        recorded = []
        for call in calls:
            recorded.append({"id": call.id, "name": call.name, "args": call.args})
            events.append(
                Event(kind="tool.call", payload={"name": call.name, "args": call.args})
            )
        self.session.add_assistant("", tool_calls=recorded)
        for call in calls:
            try:
                result = self.tools.call(call.name, call.args)
                output = result.output
            except ToolError as exc:
                output = f"tool error: {exc}"
            self.session.add_tool(call.id, output)
            events.append(
                Event(kind="tool.result", payload={"name": call.name, "output": output})
            )
