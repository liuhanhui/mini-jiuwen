from pathlib import Path

from fastapi.testclient import TestClient

from mini_swarm.doorbell.agentserver import create_agentserver_app
from mini_swarm.doorbell.envelope import encode_request
from mini_swarm.engine.model import ModelTurn, ScriptedModel


def test_agentserver_ws_dispatches_chat_send(tmp_path: Path, caplog) -> None:
    app = create_agentserver_app(
        workspace=tmp_path,
        model=ScriptedModel([ModelTurn(text="hello")]),
    )
    caplog.set_level("INFO")
    with TestClient(app).websocket_connect("/e2a") as ws:
        ws.send_text(
            encode_request(session_id="s1", request_id="req-1", query="hi")
        )
        chunk = ws.receive_json()
        complete = ws.receive_json()

    assert chunk["type"] == "chunk"
    assert chunk["kind"] == "text.delta"
    assert chunk["payload"]["text"] == "hello"
    assert complete == {"type": "complete", "request_id": "req-1"}
    assert "dispatched to runner" in caplog.text
    assert "req-1" in caplog.text


def test_agentserver_ws_rejects_unknown_method(tmp_path: Path) -> None:
    app = create_agentserver_app(
        workspace=tmp_path,
        model=ScriptedModel([ModelTurn(text="nope")]),
    )
    with TestClient(app).websocket_connect("/e2a") as ws:
        ws.send_text(
            '{"session_id":"s1","request_id":"r9","method":"ping","query":""}'
        )
        error = ws.receive_json()
    assert error["type"] == "error"
    assert error["request_id"] == "r9"
    assert "chat.send" in error["message"]
