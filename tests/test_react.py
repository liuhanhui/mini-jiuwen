from pathlib import Path

from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def test_react_calls_read_file_then_answers(tmp_path: Path) -> None:
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
    agent = ReactAgent(
        model=model,
        tools=make_default_tools(tmp_path),
        session=Session(session_id="demo", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=8),
    )

    result = agent.run("What is the first line of README?")

    assert result.final_text == "The first line is first line"
    assert any(event.kind == "tool.call" for event in result.events)
    assert (tmp_path / "sessions" / "demo.json").exists()


def test_react_stops_at_max_steps_without_final_text(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c1", name="read_file", args={"path": "missing.md"})
                ]
            ),
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c2", name="read_file", args={"path": "missing.md"})
                ]
            ),
        ]
    )
    agent = ReactAgent(
        model=model,
        tools=make_default_tools(tmp_path),
        session=Session(session_id="loop", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )

    result = agent.run("keep going")

    assert result.stopped_by == "max_steps"
    assert result.final_text is None
    assert model.remaining() == 0


def test_react_loop_lives_only_in_react_module() -> None:
    """Doorbell modules must not contain the model while-loop (constitution)."""
    root = Path(__file__).resolve().parents[1] / "src" / "mini_swarm"
    offenders = []
    for path in root.rglob("*.py"):
        if path.name == "react.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "model.complete" in text or "model.chat" in text or "model.stream" in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == []
