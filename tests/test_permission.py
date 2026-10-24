import asyncio
from pathlib import Path

import pytest

from mini_swarm.engine.deep_agent import DeepAgent, DeepAgentError
from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools

WRITE_CMD = (
    "python -c \"from pathlib import Path; "
    "Path('pwned.txt').write_text('boom', encoding='utf-8')\""
)


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


def _bash_model(*after: ModelTurn) -> ScriptedModel:
    return ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="b1", name="bash", args={"command": WRITE_CMD})
                ]
            ),
            *after,
        ]
    )


def test_read_file_does_not_ask_permission(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok\n", encoding="utf-8")
    agent = _agent(
        tmp_path,
        ScriptedModel(
            [
                ModelTurn(
                    tool_calls=[
                        ToolCall(id="c1", name="read_file", args={"path": "README.md"})
                    ]
                ),
                ModelTurn(text="ok"),
            ]
        ),
    )
    agent.send_input("read it")
    kinds = [event.kind for event in _collect(agent)]
    assert "permission.ask" not in kinds
    assert kinds[-1] == "turn.complete"


def test_bash_pauses_and_does_not_run_until_allow(tmp_path: Path) -> None:
    agent = _agent(tmp_path, _bash_model(ModelTurn(text="done")))
    agent.send_input("write a file")
    events = _collect(agent)

    assert any(event.kind == "permission.ask" for event in events)
    assert not (tmp_path / "pwned.txt").exists()

    agent.send_input(decision="allow")
    _collect(agent)
    assert (tmp_path / "pwned.txt").read_text(encoding="utf-8") == "boom"


def test_bash_deny_does_not_run_and_observes_refusal(tmp_path: Path) -> None:
    agent = _agent(tmp_path, _bash_model(ModelTurn(text="I stopped")))
    agent.send_input("write a file")
    _collect(agent)

    agent.send_input(decision="deny")
    events = _collect(agent)

    assert not (tmp_path / "pwned.txt").exists()
    results = [e for e in events if e.kind == "tool.result"]
    assert results[0].payload["output"] == "用户拒绝"
    assert events[-2].payload["text"] == "I stopped"


def test_permission_pending_survives_new_agent_from_disk(tmp_path: Path) -> None:
    model = _bash_model(ModelTurn(text="done"))
    agent = _agent(tmp_path, model)
    agent.send_input("write a file")
    _collect(agent)

    loaded = Session.load("s1", tmp_path / "sessions")
    assert loaded.pending_calls
    resumed = DeepAgent(
        model=model,
        tools=make_default_tools(tmp_path),
        session=loaded,
        stop=StopPolicy(max_steps=8),
    )
    resumed.send_input(decision="allow")
    _collect(resumed)
    assert (tmp_path / "pwned.txt").exists()
    assert Session.load("s1", tmp_path / "sessions").pending_calls is None


def test_decision_without_pending_permission_raises(tmp_path: Path) -> None:
    agent = _agent(tmp_path, ScriptedModel([ModelTurn(text="hi")]))
    agent.send_input(decision="allow")
    with pytest.raises(DeepAgentError, match="pending"):
        _collect(agent)
