from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from mini_swarm.doorbell.envelope import (
    EnvelopeError,
    decode_request,
    encode_chunk,
    encode_complete,
    encode_error,
    peek_request_id,
)
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.team import make_team

logger = logging.getLogger("mini_swarm.agentserver")


def create_agentserver_app(
    *,
    workspace: Path,
    model: object,
    rail_path: str | Path | None = None,
) -> FastAPI:
    workspace = Path(workspace)
    store_dir = workspace / "sessions"
    stop = StopPolicy(max_steps=8)
    app = FastAPI(title="Mini JiuwenSwarm AgentServer")

    @app.websocket("/e2a")
    async def e2a(ws: WebSocket) -> None:
        await ws.accept()
        while True:
            try:
                raw = await ws.receive_text()
            except WebSocketDisconnect:
                break
            try:
                envelope = decode_request(raw)
            except EnvelopeError as exc:
                await ws.send_text(encode_error(peek_request_id(raw), str(exc)))
                continue
            logger.info(
                "dispatched to runner session_id=%s request_id=%s",
                envelope.session_id,
                envelope.request_id,
            )
            team = make_team(
                workspace=workspace,
                model=model,
                session_id=envelope.session_id,
                stop=stop,
                rail_path=rail_path,
                store_dir=store_dir,
            )
            if envelope.decision:
                team.send_input(decision=envelope.decision)
            else:
                team.send_input(envelope.query)
            async for event in team.attach_output():
                if event.kind == "turn.complete":
                    continue
                await ws.send_text(
                    encode_chunk(
                        envelope.request_id,
                        kind=event.kind,
                        payload=event.payload,
                    )
                )
            await ws.send_text(encode_complete(envelope.request_id))

    return app
