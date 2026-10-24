from pathlib import Path

from mini_swarm.engine.compact import CompactPolicy, compact_messages
from mini_swarm.engine.model import ModelTurn
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def test_compact_leaves_short_history_alone() -> None:
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    compacted, info = compact_messages(
        messages, CompactPolicy(max_messages=8, keep_recent=4)
    )
    assert compacted == messages
    assert info is None


def test_compact_folds_prefix_into_one_note() -> None:
    messages = []
    for i in range(6):
        messages.append({"role": "user", "content": f"q{i}"})
        messages.append({"role": "assistant", "content": f"a{i}"})

    compacted, info = compact_messages(
        messages, CompactPolicy(max_messages=6, keep_recent=4)
    )

    assert info == {"dropped": 8, "kept": 4}
    assert compacted[0]["role"] == "user"
    assert compacted[0]["content"].startswith("[compacted]")
    assert "q0" in compacted[0]["content"]
    assert compacted[-4:] == messages[-4:]
    assert all(item.get("content") != "q0" for item in compacted[1:])


def test_compact_does_not_start_tail_with_tool() -> None:
    messages = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "old-a"},
        {"role": "user", "content": "read it"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "name": "read_file", "args": {"path": "README.md"}}],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "hello"},
        {"role": "assistant", "content": "done"},
    ]

    compacted, info = compact_messages(
        messages, CompactPolicy(max_messages=4, keep_recent=2)
    )

    assert info is not None
    assert compacted[1]["role"] != "tool"
    assert any(item.get("role") == "tool" for item in compacted)


def test_react_compacts_long_session_before_complete(tmp_path: Path) -> None:
    session = Session(session_id="long", store_dir=tmp_path / "sessions")
    for i in range(5):
        session.add_user(f"old-{i}")
        session.add_assistant(f"ans-{i}")
    seen: list[list[dict]] = []

    class CaptureModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del tools
            seen.append([dict(message) for message in messages])
            return ModelTurn(text="fresh")

    agent = ReactAgent(
        model=CaptureModel(),
        tools=make_default_tools(tmp_path),
        session=session,
        stop=StopPolicy(max_steps=2),
        compact=CompactPolicy(max_messages=6, keep_recent=2),
    )

    result = agent.run("what now?")

    assert result.final_text == "fresh"
    assert any(event.kind == "context.compact" for event in result.events)
    dialogue = [message for message in seen[0] if message.get("role") != "system"]
    assert dialogue[0]["content"].startswith("[compacted]")
    assert dialogue[-1] == {"role": "user", "content": "what now?"}
    saved = Session.load("long", tmp_path / "sessions")
    assert saved.messages[0]["content"].startswith("[compacted]")
    assert len(saved.messages) < 12
