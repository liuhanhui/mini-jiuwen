import json

import pytest

from mini_swarm.engine.llm import LlmError, OpenAICompatModel, to_openai_messages, to_openai_tools
from mini_swarm.engine.model import ToolCall


def test_to_openai_messages_maps_tool_rounds() -> None:
    mapped = to_openai_messages(
        [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c1", "name": "read_file", "args": {"path": "README.md"}}],
            },
            {"role": "tool", "tool_call_id": "c1", "content": "hello"},
        ]
    )
    assert mapped[0] == {"role": "user", "content": "hi"}
    assert mapped[1]["tool_calls"][0]["function"]["name"] == "read_file"
    assert json.loads(mapped[1]["tool_calls"][0]["function"]["arguments"]) == {
        "path": "README.md"
    }
    assert mapped[2] == {"role": "tool", "tool_call_id": "c1", "content": "hello"}


def test_to_openai_tools_wraps_registry_schemas() -> None:
    tools = to_openai_tools(
        [{"name": "read_file", "description": "Read a file", "parameters": {"path": "relative"}}]
    )
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "read_file"
    assert tools[0]["function"]["parameters"]["properties"]["path"]["type"] == "string"


def test_complete_returns_tool_calls_from_openai_payload() -> None:
    model = OpenAICompatModel(api_key="k", base_url="https://example.test/v1", model="demo")
    model._post = lambda payload: {  # type: ignore[method-assign]
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "c1",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path": "README.md"}',
                            },
                        }
                    ]
                }
            }
        ]
    }
    turn = model.complete([{"role": "user", "content": "hi"}], [{"name": "read_file"}])
    assert turn.tool_calls == [
        ToolCall(id="c1", name="read_file", args={"path": "README.md"})
    ]


def test_complete_returns_text_when_no_tool_calls() -> None:
    model = OpenAICompatModel(api_key="k", base_url="https://example.test/v1", model="demo")
    model._post = lambda payload: {  # type: ignore[method-assign]
        "choices": [{"message": {"content": "hello"}}]
    }
    turn = model.complete([{"role": "user", "content": "hi"}], [])
    assert turn.text == "hello"
    assert not turn.tool_calls


def test_from_env_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("MINI_SWARM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LlmError, match="API_KEY"):
        OpenAICompatModel.from_env()
