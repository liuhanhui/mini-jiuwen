from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.react import Event
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.task import install_task_tool
from mini_swarm.engine.tools import ToolRegistry, ToolResult
from mini_swarm.rail import make_harness_tools


class Team:
    """Same-process Leader + Teammate. Doorbell talks to the leader only."""

    def __init__(self, leader: DeepAgent, teammate: DeepAgent) -> None:
        self.leader = leader
        self.teammate = teammate

    def send_input(self, query: str | None = None, *, decision: str | None = None) -> None:
        self.leader.send_input(query, decision=decision)

    async def attach_output(self) -> AsyncIterator[Event]:
        async for event in self.leader.attach_output():
            yield event


def _open_session(session_id: str, store_dir: Path) -> Session:
    if (Path(store_dir) / f"{session_id}.json").exists():
        return Session.load(session_id, store_dir)
    return Session(session_id=session_id, store_dir=store_dir)


def install_ask_teammate(tools: ToolRegistry, teammate: DeepAgent) -> None:
    if "ask_teammate" not in tools.names():
        return

    def _ask(args: dict) -> ToolResult:
        prompt = str(args.get("prompt") or args.get("query") or "").strip()
        if not prompt:
            return ToolResult(ok=False, output="empty teammate prompt")
        result = teammate._react.run(prompt)
        output = result.final_text or ""
        if not output:
            output = f"stopped_by={result.stopped_by}"
        return ToolResult(ok=True, output=output)

    tools.replace_handler("ask_teammate", _ask)


def make_team(
    *,
    workspace: Path,
    model: object,
    session_id: str,
    stop: StopPolicy | None = None,
    rail_path: str | Path | None = None,
    store_dir: Path | None = None,
) -> Team:
    workspace = Path(workspace)
    stop = stop or StopPolicy()
    store_dir = Path(store_dir) if store_dir else workspace / "sessions"
    leader_tools = make_harness_tools(
        workspace, rail_path, model=model, stop=stop, store_dir=store_dir
    )
    teammate_names = [name for name in leader_tools.names() if name != "ask_teammate"]
    teammate_tools = ToolRegistry(workspace, enabled=teammate_names)
    install_task_tool(
        teammate_tools, model=model, stop=stop, store_dir=store_dir
    )
    teammate = DeepAgent(
        model=model,
        tools=teammate_tools,
        session=_open_session(f"{session_id}-teammate", store_dir),
        stop=stop,
    )
    install_ask_teammate(leader_tools, teammate)
    leader = DeepAgent(
        model=model,
        tools=leader_tools,
        session=_open_session(session_id, store_dir),
        stop=stop,
    )
    return Team(leader, teammate)
