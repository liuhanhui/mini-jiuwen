import json
from pathlib import Path

from fastapi.testclient import TestClient

from mini_swarm.doorbell.http import create_app
from mini_swarm.engine.model import ModelTurn, ScriptedModel


def _lines(response) -> list[dict]:
    return [json.loads(line) for line in response.text.strip().splitlines() if line]


def test_post_chat_streams_ndjson_events(tmp_path: Path) -> None:
    app = create_app(
        workspace=tmp_path,
        model=ScriptedModel([ModelTurn(text="hello")]),
    )
    response = TestClient(app).post("/chat", json={"session_id": "s1", "query": "hi"})

    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers["content-type"]
    lines = _lines(response)
    assert [item["kind"] for item in lines] == ["text.delta", "turn.complete"]
    assert lines[0]["payload"]["text"] == "hello"


def test_chat_survives_app_restart_with_same_session(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelTurn(text="hello"),
            ModelTurn(text="again"),
        ]
    )
    TestClient(create_app(workspace=tmp_path, model=model)).post(
        "/chat", json={"session_id": "s1", "query": "hi"}
    )

    response = TestClient(create_app(workspace=tmp_path, model=model)).post(
        "/chat", json={"session_id": "s1", "query": "next"}
    )
    lines = _lines(response)
    assert lines[0]["payload"]["text"] == "again"

    saved = json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))
    contents = [msg["content"] for msg in saved["messages"]]
    assert contents == ["hi", "hello", "next", "again"]


def test_http_doorbell_only_wakes_deep_agent() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "src" / "mini_swarm" / "doorbell" / "http.py"
    ).read_text(encoding="utf-8")
    assert "send_input" in source
    assert "attach_output" in source
    assert "ReactAgent" not in source
    assert "model.complete" not in source
