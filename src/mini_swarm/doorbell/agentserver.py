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
from mini_swarm.doorbell.sessions import open_session
from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools

logger = logging.getLogger("mini_swarm.agentserver")


def create_agentserver_app(*, workspace: Path, model: object) -> FastAPI:
    workspace = Path(workspace)
    store_dir = workspace / "sessions"
    tools = make_default_tools(workspace)
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
            agent = DeepAgent(
                model=model,
                tools=tools,
                session=open_session(envelope.session_id, store_dir),
                stop=StopPolicy(max_steps=8),
            )
            if envelope.decision:
                agent.send_input(decision=envelope.decision)
            else:
                agent.send_input(envelope.query)
            async for event in agent.attach_output():
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
