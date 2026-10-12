import pytest

from mini_swarm.doorbell.envelope import (
    EnvelopeError,
    decode_request,
    decode_response,
    encode_chunk,
    encode_complete,
    encode_error,
    encode_request,
)


def test_roundtrip_chat_send() -> None:
    raw = encode_request(
        session_id="s1",
        request_id="r1",
        query="hello",
    )
    env = decode_request(raw)
    assert env.session_id == "s1"
    assert env.request_id == "r1"
    assert env.method == "chat.send"
    assert env.query == "hello"


def test_rejects_methods_other_than_chat_send() -> None:
    raw = '{"session_id":"s1","request_id":"r1","method":"chat.cancel","query":"x"}'
    with pytest.raises(EnvelopeError, match="chat.send"):
        decode_request(raw)


def test_response_frames_roundtrip() -> None:
    chunk = decode_response(
        encode_chunk("r1", kind="text.delta", payload={"text": "hi"})
    )
    assert chunk == {
        "type": "chunk",
        "request_id": "r1",
        "kind": "text.delta",
        "payload": {"text": "hi"},
    }
    assert decode_response(encode_complete("r1"))["type"] == "complete"
    error = decode_response(encode_error("r1", "AgentServer unavailable"))
    assert error["type"] == "error"
    assert "unavailable" in error["message"]
