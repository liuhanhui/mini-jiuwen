from __future__ import annotations

from collections.abc import AsyncIterator

from mini_swarm.engine.react import Event, Model, ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import ToolRegistry


class DeepAgentError(Exception):
    pass


class DeepAgent:
    """Public harness handle. Doorbell code may only call send_input / attach_output."""

    def __init__(
        self,
        model: Model,
        tools: ToolRegistry,
        session: Session,
        stop: StopPolicy | None = None,
    ) -> None:
        self.session = session
        self._react = ReactAgent(model=model, tools=tools, session=session, stop=stop)
        self._pending_query: str | None = None

    def send_input(self, query: str) -> None:
        self._pending_query = query

    async def attach_output(self) -> AsyncIterator[Event]:
        if self._pending_query is None:
            raise DeepAgentError("send_input before attach_output")
        query = self._pending_query
        self._pending_query = None
        result = self._react.run(query)
        for event in result.events:
            yield event
