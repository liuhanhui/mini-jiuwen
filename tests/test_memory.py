from pathlib import Path

from mini_swarm.engine.memory import load_memory_messages, messages_with_memory
from mini_swarm.engine.model import ModelTurn, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def test_load_memory_messages_reads_agents_and_memory(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Be brief.\n", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text("User likes tea.\n", encoding="utf-8")

    messages = load_memory_messages(tmp_path)

    assert messages[0]["role"] == "system"
    assert "AGENTS.md" in messages[0]["content"]
    assert "Be brief." in messages[0]["content"]
    assert messages[1]["role"] == "system"
    assert "MEMORY.md" in messages[1]["content"]
    assert "User likes tea." in messages[1]["content"]


def test_load_memory_messages_skips_missing_and_empty_files(tmp_path: Path) -> None:
    (tmp_path / "MEMORY.md").write_text("   \n", encoding="utf-8")

    assert load_memory_messages(tmp_path) == []


def test_messages_with_memory_prepends_without_mutating(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Stay in workspace.", encoding="utf-8")
    session_messages = [{"role": "user", "content": "hi"}]

    combined = messages_with_memory(tmp_path, session_messages)

    assert combined[0]["content"].startswith("# AGENTS.md")
    assert combined[1] == {"role": "user", "content": "hi"}
    assert session_messages == [{"role": "user", "content": "hi"}]


def test_react_injects_memory_into_complete_but_not_session(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Answer with the word orange.", encoding="utf-8")
    seen: list[list[dict]] = []

    class CaptureModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del tools
            seen.append([dict(message) for message in messages])
            return ModelTurn(text="orange")

    agent = ReactAgent(
        model=CaptureModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="mem", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )

    result = agent.run("favorite color?")

    assert result.final_text == "orange"
    assert seen[0][0]["role"] == "system"
    assert "Answer with the word orange." in seen[0][0]["content"]
    assert seen[0][1] == {"role": "user", "content": "favorite color?"}
    assert all(message.get("role") != "system" for message in agent.session.messages)
    saved = Session.load("mem", tmp_path / "sessions")
    assert all(message.get("role") != "system" for message in saved.messages)


def test_react_rereads_memory_after_write_file(tmp_path: Path) -> None:
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
                            name="write_file",
                            args={"path": "MEMORY.md", "content": "User likes tea."},
                        )
                    ]
                )
            return ModelTurn(text="noted")

    agent = ReactAgent(
        model=CaptureModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="fresh", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=4),
    )

    agent.run("remember that I like tea")

    assert len(seen) == 2
    assert all("User likes tea." not in str(message) for message in seen[0])
    assert any(
        message.get("role") == "system" and "User likes tea." in message["content"]
        for message in seen[1]
    )
