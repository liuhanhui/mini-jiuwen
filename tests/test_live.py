import asyncio
from pathlib import Path

from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.model import ModelTurn, Token
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


def test_attach_output_forwards_delta_before_model_finishes(tmp_path: Path) -> None:
    order: list[str] = []

    class ProbeModel:
        def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
            del messages, tools
            return ModelTurn(text="Hel")

        def stream(self, messages: list[dict], tools: list[dict]):
            del messages, tools
            yield Token("Hel")
            order.append("model-continued")
            yield ModelTurn(text="Hel")

    agent = DeepAgent(
        model=ProbeModel(),
        tools=make_default_tools(tmp_path),
        session=Session(session_id="live", store_dir=tmp_path / "sessions"),
        stop=StopPolicy(max_steps=2),
    )
    agent.send_input("hi")

    async def _run() -> None:
        async for event in agent.attach_output():
            if event.kind == "text.delta":
                order.append("doorbell-saw-delta")

    asyncio.run(_run())

    assert order == ["doorbell-saw-delta", "model-continued"]
