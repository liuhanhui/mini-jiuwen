from pathlib import Path

from mini_swarm.engine.llm import OpenAICompatModel
from mini_swarm.engine.model import ModelTurn, Token, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def test_stream_emits_text_tokens_then_turn() -> None:
    model = OpenAICompatModel(api_key="k", base_url="https://example.test/v1", model="demo")
    model._post_stream = lambda payload: iter(  # type: ignore[method-assign]
        [
            {"choices": [{"delta": {"content": "Hel"}}]},
            {"choices": [{"delta": {"content": "lo"}}]},
        ]
    )

    parts = list(model.stream([{"role": "user", "content": "hi"}], []))

    assert [part.text for part in parts if isinstance(part, Token)] == ["Hel", "lo"]
    assert parts[-1] == ModelTurn(text="Hello")


def test_stream_assembles_tool_calls_without_tokens() -> None:
    model = OpenAICompatModel(api_key="k", base_url="https://example.test/v1", model="demo")
    model._post_stream = lambda payload: iter(  # type: ignore[method-assign]
        [
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {"name": "read_file", "arguments": ""},
                                }
                            ]
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": '{"path": "README.md"}'},
                                }
                            ]
                        }
                    }
                ]
            },
        ]
    )

    parts = list(model.stream([{"role": "user", "content": "hi"}], [{"name": "read_file"}]))

    assert not any(isinstance(part, Token) for part in parts)
    assert parts[-1].tool_calls == [
        ToolCall(id="c1", name="read_file", args={"path": "README.md"})
    ]


def test_react_emits_incremental_text_delta(tmp_path: Path) -> None:
    class StreamModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del messages, tools
            return ModelTurn(text="Hello")

        def stream(self, messages: list[dict], tools: list[dict]):
            del messages, tools
            yield Token("Hel")
            yield Token("lo")
            yield ModelTurn(text="Hello")

    agent = ReactAgent(
        model=StreamModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="stream", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )

    result = agent.run("hi")

    deltas = [
        event.payload["text"] for event in result.events if event.kind == "text.delta"
    ]
    assert deltas == ["Hel", "lo"]
    assert result.final_text == "Hello"
    assert result.events[-1].kind == "turn.complete"
