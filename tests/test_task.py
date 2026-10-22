from pathlib import Path

from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.task import install_task_tool
from mini_swarm.engine.tools import make_default_tools
from mini_swarm.rail import make_rail_tools


def _parent(tmp_path: Path, model: ScriptedModel) -> ReactAgent:
    tools = make_default_tools(tmp_path)
    install_task_tool(
        tools,
        model=model,
        stop=StopPolicy(max_steps=8),
        store_dir=tmp_path / "sessions",
    )
    return ReactAgent(
        model=model,
        tools=tools,
        session=Session(session_id="parent", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=8),
    )


def test_task_spawns_isolated_session_and_returns_child_text(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("secret-child\n", encoding="utf-8")
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(
                        id="t1",
                        name="task",
                        args={"prompt": "Read README and report the first line"},
                    )
                ]
            ),
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c1", name="read_file", args={"path": "README.md"})
                ]
            ),
            ModelTurn(text="child: secret-child"),
            ModelTurn(text="parent heard: child: secret-child"),
        ]
    )
    agent = _parent(tmp_path, model)
    result = agent.run("delegate the read")

    assert result.final_text == "parent heard: child: secret-child"
    task_results = [e for e in result.events if e.kind == "tool.result"]
    assert task_results[0].payload["name"] == "task"
    assert task_results[0].payload["output"] == "child: secret-child"

    child_files = list((tmp_path / "sessions").glob("task-*.json"))
    assert len(child_files) == 1
    child = Session.load(child_files[0].stem, tmp_path / "sessions")
    assert child.messages[0]["content"] == "Read README and report the first line"
    assert all(msg.get("content") != "delegate the read" for msg in child.messages)


def test_child_agent_does_not_get_task_tool(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="t1", name="task", args={"prompt": "try nested"})
                ]
            ),
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c1", name="task", args={"prompt": "nope"})
                ]
            ),
            ModelTurn(text="child stopped"),
            ModelTurn(text="parent done"),
        ]
    )
    agent = _parent(tmp_path, model)
    result = agent.run("nest")
    child_files = list((tmp_path / "sessions").glob("task-*.json"))
    child = Session.load(child_files[0].stem, tmp_path / "sessions")
    tool_msgs = [m for m in child.messages if m.get("role") == "tool"]
    assert "unknown" in tool_msgs[0]["content"]
    assert result.final_text == "parent done"


def test_rail_can_enable_task(tmp_path: Path) -> None:
    rail = tmp_path / "rail.yaml"
    rail.write_text("tools:\n  - read_file\n  - task\n", encoding="utf-8")
    tools = make_rail_tools(tmp_path, rail)
    names = {schema["name"] for schema in tools.schemas()}
    assert names == {"read_file", "task"}
