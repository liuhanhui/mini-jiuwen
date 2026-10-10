import asyncio
from pathlib import Path

import pytest

from mini_swarm.engine.deep_agent import DeepAgent, DeepAgentError
from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def _collect(agent: DeepAgent):
    async def _run():
        return [event async for event in agent.attach_output()]

    return asyncio.run(_run())


def _agent(tmp_path: Path, model: ScriptedModel, session_id: str = "s1") -> DeepAgent:
    return DeepAgent(
        model=model,
        tools=make_default_tools(tmp_path),
        session=Session(session_id=session_id, store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=8),
    )


def test_send_input_then_attach_output_streams_harness_events(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("first line\n", encoding="utf-8")
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c1", name="read_file", args={"path": "README.md"})
                ]
            ),
            ModelTurn(text="The first line is first line"),
        ]
    )
    agent = _agent(tmp_path, model)
    agent.send_input("What is the first line of README?")

    events = _collect(agent)
    kinds = [event.kind for event in events]

    assert "tool.call" in kinds
    assert "text.delta" in kinds
    assert kinds[-1] == "turn.complete"
    assert events[-2].payload["text"] == "The first line is first line"


def test_attach_output_without_send_input_raises(tmp_path: Path) -> None:
    agent = _agent(tmp_path, ScriptedModel([ModelTurn(text="unused")]))

    with pytest.raises(DeepAgentError, match="send_input"):
        _collect(agent)


def test_new_agent_resumes_session_from_disk(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelTurn(text="hello"),
            ModelTurn(text="again"),
        ]
    )
    agent = _agent(tmp_path, model, session_id="s1")
    agent.send_input("hi")
    _collect(agent)

    loaded = Session.load("s1", tmp_path / "sessions")
    resumed = DeepAgent(
        model=model,
        tools=make_default_tools(tmp_path),
        session=loaded,
        stop=StopPolicy(max_steps=8),
    )
    resumed.send_input("follow up")
    events = _collect(resumed)

    assert events[-2].payload["text"] == "again"
    roles = [(msg["role"], msg.get("content")) for msg in loaded.messages]
    assert roles == [
        ("user", "hi"),
        ("assistant", "hello"),
        ("user", "follow up"),
        ("assistant", "again"),
    ]
