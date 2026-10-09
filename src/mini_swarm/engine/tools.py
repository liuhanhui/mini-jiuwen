from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class ToolError(Exception):
    pass


@dataclass
class ToolResult:
    ok: bool
    output: str


class ToolRegistry:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace).resolve()
        self._handlers: dict[str, Callable[[dict[str, Any]], ToolResult]] = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "bash": self._bash,
        }

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "Read a UTF-8 text file inside the workspace.",
                "parameters": {"path": "relative path"},
            },
            {
                "name": "write_file",
                "description": "Write a UTF-8 text file inside the workspace.",
                "parameters": {"path": "relative path", "content": "file contents"},
            },
            {
                "name": "bash",
                "description": "Run a shell command with the workspace as cwd.",
                "parameters": {"command": "shell command"},
            },
        ]

    def call(self, name: str, args: dict[str, Any]) -> ToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            raise ToolError(f"unknown tool: {name}")
        return handler(args)

    def resolve(self, relative: str) -> Path:
        if not relative or Path(relative).is_absolute():
            raise ToolError("path must be relative to the workspace")
        candidate = (self.workspace / relative).resolve()
        if not candidate.is_relative_to(self.workspace):
            raise ToolError("path escapes workspace")
        return candidate

    def _read_file(self, args: dict[str, Any]) -> ToolResult:
        path = self.resolve(str(args.get("path") or ""))
        if not path.is_file():
            return ToolResult(ok=False, output=f"file not found: {args.get('path')}")
        text = path.read_text(encoding="utf-8-sig")
        return ToolResult(ok=True, output=text)

    def _write_file(self, args: dict[str, Any]) -> ToolResult:
        path = self.resolve(str(args.get("path") or ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(args.get("content") or ""), encoding="utf-8")
        return ToolResult(ok=True, output=f"wrote {args.get('path')}")

    def _bash(self, args: dict[str, Any]) -> ToolResult:
        command = str(args.get("command") or "").strip()
        if not command:
            return ToolResult(ok=False, output="empty command")
        completed = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        if completed.returncode != 0:
            return ToolResult(ok=False, output=output or f"exit {completed.returncode}")
        return ToolResult(ok=True, output=output)


def make_default_tools(workspace: Path) -> ToolRegistry:
    return ToolRegistry(workspace)
