import asyncio
from pathlib import Path

import pytest

from mini_swarm.engine.deep_agent import DeepAgent, DeepAgentError
from mini_swarm.engine.model import ModelTurn, ScriptedModel, Token
from mini_swarm.engine.react import Event
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def _collect(agent: DeepAgent):
    async def _run():
        return [event async for event in agent.attach_output()]

    return asyncio.run(_run())


def test_cancel_stops_before_the_next_token(tmp_path: Path) -> None:
    agent_box: list[DeepAgent] = []

    class ProbeModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del messages, tools
            return ModelTurn(text="Hello")

        def stream(self, messages: list[dict], tools: list[dict]):
            del messages, tools
            yield Token("Hel")
            agent_box[0].send_input(decision="cancel")
            yield Token("lo")
            yield ModelTurn(text="Hello")

    agent = DeepAgent(
        model=ProbeModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="cancel", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )
    agent_box.append(agent)
    agent.send_input("hi")

    events = _collect(agent)
    kinds = [event.kind for event in events]
    texts = [
        event.payload.get("text")
        for event in events
        if event.kind == Event.TEXT_DELTA
    ]

    assert Event.TEXT_DELTA in kinds
    assert texts == ["Hel"]
    assert kinds[-1] == Event.CANCELLED
    assert Event.TURN_COMPLETE not in kinds


def test_unknown_decision_is_rejected(tmp_path: Path) -> None:
    agent = DeepAgent(
        model=ScriptedModel([ModelTurn(text="x")]),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="dec", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )
    with pytest.raises(DeepAgentError, match="allow or deny or cancel"):
        agent.send_input(decision="nope")
