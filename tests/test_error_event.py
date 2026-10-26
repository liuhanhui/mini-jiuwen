import asyncio
from pathlib import Path

from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.llm import LlmError
from mini_swarm.engine.model import ModelTurn
from mini_swarm.engine.react import Event
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def _collect(agent: DeepAgent):
    async def _run():
        return [event async for event in agent.attach_output()]

    return asyncio.run(_run())


def test_llm_error_becomes_error_event_not_exception(tmp_path: Path) -> None:
    class BoomModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del messages, tools
            raise LlmError("model HTTP 401: unauthorized")

        def stream(self, messages: list[dict], tools: list[dict]):
            del messages, tools
            raise LlmError("model HTTP 401: unauthorized")
            yield ModelTurn(text="unused")

    agent = DeepAgent(
        model=BoomModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="err", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )
    agent.send_input("hi")

    events = _collect(agent)

    assert [event.kind for event in events] == [Event.ERROR]
    assert "401" in events[0].payload["message"]
    assert events[0].payload["message"]


def test_event_kinds_are_declared_on_event() -> None:
    assert Event.TEXT_DELTA == "text.delta"
    assert Event.ERROR == "error"
    assert Event.TURN_COMPLETE == "turn.complete"


def test_chat_page_uses_the_same_kind_strings() -> None:
    from mini_swarm.channels.web.page import CHAT_PAGE

    assert Event.TEXT_DELTA in CHAT_PAGE
    assert Event.TOOL_CALL in CHAT_PAGE
    assert Event.PERMISSION_ASK in CHAT_PAGE
    assert Event.ERROR in CHAT_PAGE
