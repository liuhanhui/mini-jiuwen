from pathlib import Path

import pytest

from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import ToolError
from mini_swarm.rail import RailError, make_rail_tools


def _write_rail(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_rail_yaml_can_drop_bash(tmp_path: Path) -> None:
    rail = _write_rail(
        tmp_path / "rail.yaml",
        "tools:\n  - read_file\n  - write_file\n",
    )
    tools = make_rail_tools(tmp_path, rail)
    names = {schema["name"] for schema in tools.schemas()}

    assert names == {"read_file", "write_file"}
    with pytest.raises(ToolError, match="unknown"):
        tools.call("bash", {"command": "echo hi"})


def test_rail_yaml_can_enable_only_read_file(tmp_path: Path) -> None:
    rail = _write_rail(tmp_path / "rail.yaml", "tools:\n  - read_file\n")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    tools = make_rail_tools(tmp_path, rail)

    result = tools.call("read_file", {"path": "README.md"})
    assert result.ok is True
    assert "hello" in result.output
    with pytest.raises(ToolError, match="unknown"):
        tools.call("write_file", {"path": "x.txt", "content": "no"})


def test_workspace_rail_yaml_is_used_when_path_omitted(tmp_path: Path) -> None:
    _write_rail(tmp_path / "rail.yaml", "tools:\n  - write_file\n")
    tools = make_rail_tools(tmp_path)
    names = {schema["name"] for schema in tools.schemas()}
    assert names == {"write_file"}


def test_missing_rail_keeps_all_builtins(tmp_path: Path) -> None:
    tools = make_rail_tools(tmp_path)
    names = {schema["name"] for schema in tools.schemas()}
    assert names == {"read_file", "write_file", "bash"}


def test_unknown_rail_tool_is_an_error(tmp_path: Path) -> None:
    rail = _write_rail(tmp_path / "rail.yaml", "tools:\n  - not_a_tool\n")
    with pytest.raises(RailError, match="not_a_tool"):
        make_rail_tools(tmp_path, rail)


def test_react_does_not_ask_permission_when_bash_not_on_rail(tmp_path: Path) -> None:
    rail = _write_rail(tmp_path / "rail.yaml", "tools:\n  - read_file\n")
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="b1", name="bash", args={"command": "echo hi"})
                ]
            ),
            ModelTurn(text="stopped"),
        ]
    )
    agent = ReactAgent(
        model=model,
        tools=make_rail_tools(tmp_path, rail),
        session=Session(session_id="s1", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=8),
    )

    result = agent.run("run bash")
    kinds = [event.kind for event in result.events]
    assert "permission.ask" not in kinds
    assert any(
        event.kind == "tool.result" and "unknown" in event.payload["output"]
        for event in result.events
    )
    assert result.final_text == "stopped"
