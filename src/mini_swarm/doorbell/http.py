from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mini_swarm.doorbell.sessions import open_session
from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.react import Event
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.rail import make_rail_tools


class ChatRequest(BaseModel):
    session_id: str
    query: str = ""
    decision: str | None = None


def _event_line(event: Event) -> str:
    return json.dumps(
        {"kind": event.kind, "payload": event.payload},
        ensure_ascii=False,
    ) + "\n"


def create_app(
    *,
    workspace: Path,
    model: object,
    rail_path: str | Path | None = None,
) -> FastAPI:
    workspace = Path(workspace)
    store_dir = workspace / "sessions"
    tools = make_rail_tools(workspace, rail_path)
    app = FastAPI(title="Mini JiuwenSwarm doorbell")

    @app.post("/chat")
    async def chat(body: ChatRequest) -> StreamingResponse:
        agent = DeepAgent(
            model=model,
            tools=tools,
            session=open_session(body.session_id, store_dir),
            stop=StopPolicy(max_steps=8),
        )
        if body.decision:
            agent.send_input(decision=body.decision)
        else:
            agent.send_input(body.query)

        async def stream() -> AsyncIterator[str]:
            async for event in agent.attach_output():
                yield _event_line(event)

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return app
