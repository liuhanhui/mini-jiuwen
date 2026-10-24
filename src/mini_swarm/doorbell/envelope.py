from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

CHAT_SEND = "chat.send"


class EnvelopeError(Exception):
    pass


@dataclass
class Envelope:
    session_id: str
    request_id: str
    method: str
    query: str
    decision: str | None = None


def encode_request(
    *,
    session_id: str,
    request_id: str,
    query: str,
    method: str = CHAT_SEND,
    decision: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "session_id": session_id,
        "request_id": request_id,
        "method": method,
        "query": query,
    }
    if decision:
        payload["decision"] = decision
    return json.dumps(payload)


def decode_request(raw: str) -> Envelope:
    data = json.loads(raw)
    method = str(data.get("method") or "")
    if method != CHAT_SEND:
        raise EnvelopeError(f"method must be {CHAT_SEND}")
    raw_decision = data.get("decision")
    return Envelope(
        session_id=str(data.get("session_id") or ""),
        request_id=str(data.get("request_id") or ""),
        method=method,
        query=str(data.get("query") or ""),
        decision=str(raw_decision) if raw_decision else None,
    )


def peek_request_id(raw: str) -> str:
    try:
        return str(json.loads(raw).get("request_id") or "")
    except json.JSONDecodeError:
        return ""


def encode_chunk(request_id: str, *, kind: str, payload: dict[str, Any]) -> str:
    return json.dumps(
        {
            "type": "chunk",
            "request_id": request_id,
            "kind": kind,
            "payload": payload,
        }
    )


def encode_complete(request_id: str) -> str:
    return json.dumps({"type": "complete", "request_id": request_id})


def encode_error(request_id: str, message: str) -> str:
    return json.dumps(
        {"type": "error", "request_id": request_id, "message": message}
    )


def decode_response(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise EnvelopeError("response must be an object")
    return data
