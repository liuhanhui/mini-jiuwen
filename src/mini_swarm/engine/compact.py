from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompactPolicy:
    max_messages: int = 24
    keep_recent: int = 8


def _snippet(message: dict) -> str:
    text = str(message.get("content") or "").strip()
    if text:
        return text[:80]
    calls = message.get("tool_calls") or []
    if calls:
        names = ", ".join(str(call.get("name") or "") for call in calls)
        return f"assistant {names}".strip()
    return str(message.get("role") or "message")


def compact_messages(
    messages: list[dict], policy: CompactPolicy | None = None
) -> tuple[list[dict], dict | None]:
    policy = policy or CompactPolicy()
    history = list(messages)
    if policy.max_messages <= 0 or len(history) <= policy.max_messages:
        return history, None
    keep = min(max(1, policy.keep_recent), max(1, policy.max_messages - 1))
    cut = len(history) - keep
    while cut > 0 and history[cut].get("role") == "tool":
        cut -= 1
    prefix = history[:cut]
    tail = history[cut:]
    if not prefix:
        return history, None
    summary = {
        "role": "user",
        "content": (
            f"[compacted] {len(prefix)} earlier messages. "
            f"First: {_snippet(prefix[0])} Last: {_snippet(prefix[-1])}"
        ),
    }
    return [summary] + tail, {"dropped": len(prefix), "kept": len(tail)}
