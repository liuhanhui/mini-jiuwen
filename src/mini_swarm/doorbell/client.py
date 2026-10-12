from __future__ import annotations

from collections.abc import AsyncIterator

from mini_swarm.doorbell.envelope import Envelope, decode_response, encode_request


class WsAgentClient:
    """Gateway → AgentServer WebSocket client."""

    def __init__(self, url: str) -> None:
        self.url = url

    async def send_chat(self, envelope: Envelope) -> AsyncIterator[dict]:
        try:
            import websockets
        except ImportError as exc:  # pragma: no cover
            raise ConnectionError("websockets package is required") from exc
        try:
            async with websockets.connect(self.url) as ws:
                await ws.send(
                    encode_request(
                        session_id=envelope.session_id,
                        request_id=envelope.request_id,
                        query=envelope.query,
                        decision=envelope.decision,
                    )
                )
                async for raw in ws:
                    frame = decode_response(raw)
                    yield frame
                    if frame.get("type") in {"complete", "error"}:
                        break
        except OSError as exc:
            raise ConnectionError(str(exc)) from exc
