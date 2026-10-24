from pathlib import Path

from mini_swarm.engine.context import messages_for_complete
from mini_swarm.engine.model import ModelTurn, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.skills import load_skill_catalog_messages
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools

SECRET = "NEVER dump this whole procedure into the first complete call."


def _write_skill(workspace: Path, name: str, body: str) -> Path:
    path = workspace / "skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_skill_catalog_lists_name_path_and_first_line(tmp_path: Path) -> None:
    _write_skill(tmp_path, "brew-tea", "# Brew tea\n\n" + SECRET)

    messages = load_skill_catalog_messages(tmp_path)

    assert len(messages) == 1
    assert messages[0]["role"] == "system"
    content = messages[0]["content"]
    assert "brew-tea" in content
    assert "skills/brew-tea/SKILL.md" in content
    assert "Brew tea" in content
    assert SECRET not in content


def test_missing_skills_dir_adds_no_catalog(tmp_path: Path) -> None:
    assert load_skill_catalog_messages(tmp_path) == []


def test_messages_for_complete_orders_memory_then_skills(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Be brief.", encoding="utf-8")
    _write_skill(tmp_path, "brew-tea", "How to brew tea.\n")
    session_messages = [{"role": "user", "content": "hi"}]

    combined = messages_for_complete(tmp_path, session_messages)

    assert combined[0]["content"].startswith("# AGENTS.md")
    assert "brew-tea" in combined[1]["content"]
    assert combined[2] == {"role": "user", "content": "hi"}
    assert session_messages == [{"role": "user", "content": "hi"}]


def test_react_injects_catalog_not_skill_body(tmp_path: Path) -> None:
    _write_skill(tmp_path, "brew-tea", "# Brew tea\n\n" + SECRET)
    seen: list[list[dict]] = []

    class CaptureModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del tools
            seen.append([dict(message) for message in messages])
            return ModelTurn(text="ok")

    agent = ReactAgent(
        model=CaptureModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="skills", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )

    agent.run("how do I brew tea?")

    catalog = seen[0][0]["content"]
    assert seen[0][0]["role"] == "system"
    assert "skills/brew-tea/SKILL.md" in catalog
    assert SECRET not in catalog
    assert all(message.get("role") != "system" for message in agent.session.messages)


def test_react_can_read_skill_file_on_demand(tmp_path: Path) -> None:
    _write_skill(tmp_path, "brew-tea", "# Brew tea\n\n" + SECRET)
    seen: list[list[dict]] = []

    class CaptureModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del tools
            seen.append([dict(message) for message in messages])
            if len(seen) == 1:
                return ModelTurn(
                    tool_calls=[
                        ToolCall(
                            id="c1",
                            name="read_file",
                            args={"path": "skills/brew-tea/SKILL.md"},
                        )
                    ]
                )
            return ModelTurn(text="boiled water first")

    agent = ReactAgent(
        model=CaptureModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="read-skill", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=4),
    )

    result = agent.run("brew tea")

    assert result.final_text == "boiled water first"
    tool_messages = [message for message in seen[1] if message.get("role") == "tool"]
    assert any(SECRET in str(message.get("content")) for message in tool_messages)
