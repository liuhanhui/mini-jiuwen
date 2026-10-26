from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from mini_swarm.engine.compact import CompactPolicy, compact_messages
from mini_swarm.engine.context import messages_for_complete
from mini_swarm.engine.model import ModelTurn, Token, ToolCall
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import ToolError, ToolRegistry

DENIED_OBSERVATION = "用户拒绝"


class Model(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn: ...
    def stream(self, messages: list[dict], tools: list[dict]): ...


@dataclass
class Event:
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    final_text: str | None
    events: list[Event]
    stopped_by: str


def _call_from_dict(raw: dict[str, Any]) -> ToolCall:
    return ToolCall(
        id=str(raw.get("id") or ""),
        name=str(raw.get("name") or ""),
        args=dict(raw.get("args") or {}),
    )


def _call_to_dict(call: ToolCall) -> dict[str, Any]:
    return {"id": call.id, "name": call.name, "args": call.args}


class ReactAgent:
    """Harness inner loop: Think → Act → Observe. The only while that calls the model."""

    def __init__(
        self,
        model: Model,
        tools: ToolRegistry,
        session: Session,
        stop: StopPolicy | None = None,
        compact: CompactPolicy | None = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.session = session
        self.stop = stop or StopPolicy()
        self.compact = compact or CompactPolicy()
        self._final_text: str | None = None
        self._stopped_by = "max_steps"

    def run(self, query: str) -> RunResult:
        events = list(self.iter_run(query))
        return RunResult(self._final_text, events, self._stopped_by)

    def resume(self, allow: bool) -> RunResult:
        events = list(self.iter_resume(allow))
        return RunResult(self._final_text, events, self._stopped_by)

    def iter_run(self, query: str):
        self.session.add_user(query)
        yield from self._iter_loop([])

    def iter_resume(self, allow: bool):
        events: list[Event] = []
        remaining = [_call_from_dict(raw) for raw in (self.session.pending_calls or [])]
        if not remaining:
            self.session.save()
            self._final_text = None
            self._stopped_by = "permission"
            return
        call = remaining.pop(0)
        if allow:
            mark = len(events)
            self._observe_call(call, events)
            yield from events[mark:]
        else:
            self.session.add_tool(call.id, DENIED_OBSERVATION)
            event = Event(
                kind="tool.result",
                payload={"name": call.name, "output": DENIED_OBSERVATION},
            )
            events.append(event)
            yield event
        mark = len(events)
        if self._drain_calls(remaining, events):
            yield from events[mark:]
            self.session.save()
            self._final_text = None
            self._stopped_by = "permission"
            return
        yield from events[mark:]
        yield from self._iter_loop(events)

    def _iter_loop(self, events: list[Event]):
        step = 0
        final_text: str | None = None
        stopped_by = "max_steps"

        while not self.stop.should_stop(step=step, has_final_text=False):
            mark = len(events)
            self._maybe_compact(events)
            yield from events[mark:]
            turn, streamed = yield from self._iter_think(events)
            step += 1

            if turn.tool_calls:
                mark = len(events)
                paused = self._apply_tool_turn(turn.tool_calls, events)
                yield from events[mark:]
                if paused:
                    stopped_by = "permission"
                    break
                continue

            final_text = turn.text or ""
            self.session.add_assistant(final_text)
            if not streamed:
                event = Event(kind="text.delta", payload={"text": final_text})
                events.append(event)
                yield event
            event = Event(kind="turn.complete", payload={})
            events.append(event)
            yield event
            stopped_by = "final_text"
            break

        self.session.save()
        self._final_text = final_text
        self._stopped_by = stopped_by

    def _iter_think(self, events: list[Event]):
        messages = messages_for_complete(self.tools.workspace, self.session.messages)
        tools = self.tools.schemas()
        stream = getattr(self.model, "stream", None)
        if stream is None:
            return self.model.complete(messages, tools), False
        turn: ModelTurn | None = None
        streamed = False
        for part in stream(messages, tools):
            if isinstance(part, Token):
                if part.text:
                    event = Event(kind="text.delta", payload={"text": part.text})
                    events.append(event)
                    streamed = True
                    yield event
            elif isinstance(part, ModelTurn):
                turn = part
        return turn or ModelTurn(text=""), streamed

    def _maybe_compact(self, events: list[Event]) -> None:
        compacted, info = compact_messages(self.session.messages, self.compact)
        if info is None:
            return
        self.session.messages = compacted
        events.append(Event(kind="context.compact", payload=info))

    def _apply_tool_turn(self, calls: list[ToolCall], events: list[Event]) -> bool:
        recorded = [_call_to_dict(call) for call in calls]
        for call in calls:
            events.append(
                Event(kind="tool.call", payload={"name": call.name, "args": call.args})
            )
        self.session.add_assistant("", tool_calls=recorded)
        return self._drain_calls(list(calls), events)

    def _drain_calls(self, remaining: list[ToolCall], events: list[Event]) -> bool:
        while remaining:
            call = remaining[0]
            if self.tools.requires_permission(call.name):
                self.session.pending_calls = [_call_to_dict(item) for item in remaining]
                events.append(
                    Event(
                        kind="permission.ask",
                        payload={
                            "name": call.name,
                            "args": call.args,
                            "call_id": call.id,
                        },
                    )
                )
                return True
            remaining.pop(0)
            self._observe_call(call, events)
        self.session.pending_calls = None
        return False

    def _observe_call(self, call: ToolCall, events: list[Event]) -> None:
        try:
            result = self.tools.call(call.name, call.args)
            output = result.output
        except ToolError as exc:
            output = f"tool error: {exc}"
        self.session.add_tool(call.id, output)
        events.append(
            Event(kind="tool.result", payload={"name": call.name, "output": output})
        )
