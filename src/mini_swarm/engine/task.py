from __future__ import annotations

import uuid
from pathlib import Path

from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import ToolRegistry, ToolResult


def install_task_tool(
    tools: ToolRegistry,
    *,
    model: object,
    store_dir: Path,
    stop: StopPolicy | None = None,
) -> None:
    if "task" not in tools.names():
        return
    child_stop = stop or StopPolicy()
    store_dir = Path(store_dir)

    def _task(args: dict) -> ToolResult:
        prompt = str(args.get("prompt") or args.get("query") or "").strip()
        if not prompt:
            return ToolResult(ok=False, output="empty task prompt")
        child_names = [name for name in tools.names() if name != "task"]
        child_tools = ToolRegistry(tools.workspace, enabled=child_names)
        child = ReactAgent(
            model=model,
            tools=child_tools,
            session=Session(
                session_id=f"task-{uuid.uuid4().hex[:8]}",
                store_dir=store_dir,
            ),
            stop=child_stop,
        )
        result = child.run(prompt)
        output = result.final_text or ""
        if not output:
            output = f"stopped_by={result.stopped_by}"
        return ToolResult(ok=True, output=output)

    tools.replace_handler("task", _task)
