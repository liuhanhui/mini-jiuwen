from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mini_swarm.engine.react import Event
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.team import make_team


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
    stop = StopPolicy(max_steps=8)
    app = FastAPI(title="Mini JiuwenSwarm doorbell")

    @app.post("/chat")
    async def chat(body: ChatRequest) -> StreamingResponse:
        team = make_team(
            workspace=workspace,
            model=model,
            session_id=body.session_id,
            stop=stop,
            rail_path=rail_path,
            store_dir=store_dir,
        )
        if body.decision:
            team.send_input(decision=body.decision)
        else:
            team.send_input(body.query)

        async def stream() -> AsyncIterator[str]:
            async for event in team.attach_output():
                yield _event_line(event)

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return app
