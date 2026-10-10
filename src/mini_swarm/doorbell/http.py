from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.react import Event
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools


class ChatRequest(BaseModel):
    session_id: str
    query: str


def _open_session(session_id: str, store_dir: Path) -> Session:
    if (store_dir / f"{session_id}.json").exists():
        return Session.load(session_id, store_dir)
    return Session(session_id=session_id, store_dir=store_dir)


def _event_line(event: Event) -> str:
    return json.dumps(
        {"kind": event.kind, "payload": event.payload},
        ensure_ascii=False,
    ) + "\n"


def create_app(*, workspace: Path, model: object) -> FastAPI:
    workspace = Path(workspace)
    store_dir = workspace / "sessions"
    tools = make_default_tools(workspace)
    app = FastAPI(title="Mini JiuwenSwarm doorbell")

    @app.post("/chat")
    async def chat(body: ChatRequest) -> StreamingResponse:
        agent = DeepAgent(
            model=model,
            tools=tools,
            session=_open_session(body.session_id, store_dir),
            stop=StopPolicy(max_steps=8),
        )
        agent.send_input(body.query)

        async def stream() -> AsyncIterator[str]:
            async for event in agent.attach_output():
                yield _event_line(event)

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return app
