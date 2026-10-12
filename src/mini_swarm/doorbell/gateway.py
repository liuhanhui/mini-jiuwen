from __future__ import annotations

import logging
import uuid
from typing import Any, Protocol

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from mini_swarm.channels.web import CHAT_PAGE
from mini_swarm.doorbell.client import WsAgentClient
from mini_swarm.doorbell.envelope import CHAT_SEND, Envelope

logger = logging.getLogger("mini_swarm.gateway")


class AgentClient(Protocol):
    async def send_chat(self, envelope: Envelope): ...


def _to_browser(frame: dict[str, Any]) -> dict[str, Any]:
    frame_type = frame.get("type")
    if frame_type == "chunk":
        return {"kind": frame.get("kind"), "payload": frame.get("payload") or {}}
    if frame_type == "complete":
        return {"kind": "turn.complete", "payload": {}}
    return {
        "kind": "error",
        "payload": {"message": str(frame.get("message") or "error")},
    }


def create_gateway_app(
    *,
    agentserver_url: str,
    agent_client: AgentClient | None = None,
) -> FastAPI:
    client: AgentClient = agent_client or WsAgentClient(agentserver_url)
    app = FastAPI(title="Mini JiuwenSwarm Gateway")

    @app.get("/")
    def index() -> HTMLResponse:
        return HTMLResponse(CHAT_PAGE)

    @app.websocket("/ws")
    async def browser_ws(ws: WebSocket) -> None:
        await ws.accept()
        while True:
            try:
                data = await ws.receive_json()
            except WebSocketDisconnect:
                break
            envelope = Envelope(
                session_id=str((data or {}).get("session_id") or "default"),
                request_id=str(uuid.uuid4()),
                method=CHAT_SEND,
                query=str((data or {}).get("query") or ""),
            )
            logger.info(
                "chat.send session_id=%s request_id=%s",
                envelope.session_id,
                envelope.request_id,
            )
            try:
                async for frame in client.send_chat(envelope):
                    await ws.send_json(_to_browser(frame))
            except (ConnectionError, OSError) as exc:
                await ws.send_json(
                    {
                        "kind": "error",
                        "payload": {
                            "message": f"AgentServer unavailable: {exc}",
                        },
                    }
                )

    return app
