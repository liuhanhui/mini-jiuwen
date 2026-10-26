from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from mini_swarm.engine.model import ModelError, ModelTurn, Token, ToolCall


class LlmError(ModelError):
    pass


def to_openai_messages(messages: list[dict]) -> list[dict]:
    mapped: list[dict] = []
    for message in messages:
        role = str(message.get("role") or "")
        if role == "assistant" and message.get("tool_calls"):
            mapped.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or None,
                    "tool_calls": [
                        {
                            "id": str(call.get("id") or ""),
                            "type": "function",
                            "function": {
                                "name": str(call.get("name") or ""),
                                "arguments": json.dumps(call.get("args") or {}),
                            },
                        }
                        for call in message.get("tool_calls") or []
                    ],
                }
            )
            continue
        if role == "tool":
            mapped.append(
                {
                    "role": "tool",
                    "tool_call_id": str(message.get("tool_call_id") or ""),
                    "content": str(message.get("content") or ""),
                }
            )
            continue
        mapped.append({"role": role, "content": str(message.get("content") or "")})
    return mapped


def to_openai_tools(tools: list[dict]) -> list[dict]:
    wrapped = []
    for tool in tools:
        params = tool.get("parameters") or {}
        properties = {
            str(name): {"type": "string", "description": str(desc)}
            for name, desc in params.items()
        }
        wrapped.append(
            {
                "type": "function",
                "function": {
                    "name": str(tool.get("name") or ""),
                    "description": str(tool.get("description") or ""),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                    },
                },
            }
        )
    return wrapped


class OpenAICompatModel:
    """OpenAI-compatible Chat Completions. Implements the Model protocol only."""

    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @classmethod
    def from_env(cls) -> OpenAICompatModel:
        api_key = os.environ.get("MINI_SWARM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LlmError("MINI_SWARM_API_KEY or OPENAI_API_KEY is required")
        return cls(
            api_key=api_key,
            base_url=os.environ.get("MINI_SWARM_BASE_URL", "https://api.openai.com/v1"),
            model=os.environ.get("MINI_SWARM_MODEL", "gpt-4o-mini"),
        )

    def _payload(self, messages: list[dict], tools: list[dict], *, stream: bool = False) -> dict:
        payload: dict = {
            "model": self.model,
            "messages": to_openai_messages(messages),
        }
        openai_tools = to_openai_tools(tools)
        if openai_tools:
            payload["tools"] = openai_tools
        if stream:
            payload["stream"] = True
        return payload

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelTurn:
        data = self._post(self._payload(messages, tools))
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError("unexpected model response") from exc
        raw_calls = message.get("tool_calls") or []
        if raw_calls:
            calls = []
            for raw in raw_calls:
                function = raw.get("function") or {}
                try:
                    args = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                calls.append(
                    ToolCall(
                        id=str(raw.get("id") or ""),
                        name=str(function.get("name") or ""),
                        args=args,
                    )
                )
            return ModelTurn(tool_calls=calls)
        return ModelTurn(text=str(message.get("content") or ""))

    def stream(self, messages: list[dict], tools: list[dict]):
        chunks: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        saw_tools = False
        for data in self._post_stream(self._payload(messages, tools, stream=True)):
            try:
                delta = data["choices"][0].get("delta") or {}
            except (KeyError, IndexError, TypeError):
                continue
            content = delta.get("content")
            if content and not saw_tools:
                piece = str(content)
                chunks.append(piece)
                yield Token(piece)
            for raw in delta.get("tool_calls") or []:
                saw_tools = True
                index = int(raw.get("index") or 0)
                slot = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                if raw.get("id"):
                    slot["id"] = str(raw["id"])
                function = raw.get("function") or {}
                if function.get("name"):
                    slot["name"] = str(function["name"])
                if function.get("arguments"):
                    slot["arguments"] += str(function["arguments"])
        if saw_tools:
            assembled = []
            for index in sorted(calls):
                slot = calls[index]
                try:
                    args = json.loads(slot["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                assembled.append(
                    ToolCall(id=slot["id"], name=slot["name"], args=args)
                )
            yield ModelTurn(tool_calls=assembled)
            return
        yield ModelTurn(text="".join(chunks))

    def _post_stream(self, payload: dict):
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                for raw in response:
                    line = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LlmError(f"model HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LlmError(f"model request failed: {exc}") from exc

    def _post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LlmError(f"model HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LlmError(f"model request failed: {exc}") from exc
        return json.loads(body)
