import os
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi.testclient import TestClient

from mini_swarm.doorbell.envelope import Envelope
from mini_swarm.doorbell.gateway import create_gateway_app
from mini_swarm.doorbell.start import (
    AGENTSERVER_PORT,
    GATEWAY_PORT,
    build_start_commands,
    child_env,
)


class _FakeAgentClient:
    def __init__(self, frames: list[dict] | None = None, *, fail: bool = False) -> None:
        self.frames = frames or []
        self.fail = fail
        self.sent: list[Envelope] = []

    async def send_chat(self, envelope: Envelope) -> AsyncIterator[dict]:
        self.sent.append(envelope)
        if self.fail:
            raise ConnectionError("connect refused")
        for frame in self.frames:
            yield frame


def test_gateway_wraps_browser_message_as_chat_send(caplog) -> None:
    client = _FakeAgentClient(
        [
            {
                "type": "chunk",
                "request_id": "ignored",
                "kind": "text.delta",
                "payload": {"text": "hello"},
            },
            {"type": "complete", "request_id": "ignored"},
        ]
    )
    app = create_gateway_app(
        agentserver_url="ws://127.0.0.1:1/e2a",
        agent_client=client,
    )
    caplog.set_level("INFO")
    with TestClient(app).websocket_connect("/ws") as ws:
        ws.send_json({"session_id": "s1", "query": "hi"})
        first = ws.receive_json()
        second = ws.receive_json()

    assert first == {"kind": "text.delta", "payload": {"text": "hello"}}
    assert second == {"kind": "turn.complete", "payload": {}}
    assert client.sent[0].method == "chat.send"
    assert client.sent[0].query == "hi"
    assert "chat.send" in caplog.text


def test_gateway_returns_error_when_agentserver_is_down() -> None:
    app = create_gateway_app(
        agentserver_url="ws://127.0.0.1:1/e2a",
        agent_client=_FakeAgentClient(fail=True),
    )
    with TestClient(app).websocket_connect("/ws") as ws:
        ws.send_json({"session_id": "s1", "query": "hi"})
        error = ws.receive_json()
    assert error["kind"] == "error"
    assert "AgentServer" in error["payload"]["message"]


def test_gateway_serves_the_chat_page() -> None:
    app = create_gateway_app(agentserver_url="ws://127.0.0.1:18765/e2a")
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/ws" in response.text
    assert "允许" in response.text
    assert "拒绝" in response.text


def test_gateway_forwards_permission_decision() -> None:
    client = _FakeAgentClient(
        [
            {"type": "complete", "request_id": "ignored"},
        ]
    )
    app = create_gateway_app(
        agentserver_url="ws://127.0.0.1:1/e2a",
        agent_client=client,
    )
    with TestClient(app).websocket_connect("/ws") as ws:
        ws.send_json({"session_id": "s1", "decision": "deny"})
        ws.receive_json()
    assert client.sent[0].decision == "deny"
    assert client.sent[0].method == "chat.send"


def test_start_commands_launch_agentserver_then_gateway() -> None:
    commands = build_start_commands(demo=True)
    assert AGENTSERVER_PORT == 18765
    assert GATEWAY_PORT == 8764
    assert commands[0][commands[0].index("--role") + 1] == "agentserver"
    assert commands[1][commands[1].index("--role") + 1] == "gateway"
    assert str(AGENTSERVER_PORT) in commands[0]
    assert str(GATEWAY_PORT) in commands[1]


def test_child_env_puts_src_on_pythonpath() -> None:
    src = Path(__file__).resolve().parents[1] / "src"
    env = child_env({"PATH": "C:\\Windows"})
    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(src)
