from __future__ import annotations

import argparse
import sys


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.react import ReactAgent
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools
from mini_swarm.workspace import resolve_workspace


def build_demo_agent(workspace, session_id: str) -> ReactAgent:
    readme = workspace / "README.md"
    if not readme.exists():
        readme.write_text("hello from mini-swarm\n", encoding="utf-8")
    first_line = readme.read_text(encoding="utf-8-sig").splitlines()[0]
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c1", name="read_file", args={"path": "README.md"})
                ]
            ),
            ModelTurn(text=f"README starts with: {first_line}"),
        ]
    )
    return ReactAgent(
        model=model,
        tools=make_default_tools(workspace),
        session=Session(session_id=session_id, store_dir=workspace / "sessions"),
        stop=StopPolicy(max_steps=8),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mini JiuwenSwarm M1 CLI")
    parser.add_argument("query", nargs="?", default="What is the first line of README?")
    parser.add_argument("--demo", action="store_true", help="Run the scripted read_file demo")
    parser.add_argument("--session", default="default")
    args = parser.parse_args(argv)
    _configure_stdio()

    if not args.demo:
        print(
            "M1 only ships a scripted demo. Pass --demo "
            "(real LLM doorbell arrives in M2).",
            file=sys.stderr,
        )
        return 2

    workspace = resolve_workspace()
    agent = build_demo_agent(workspace, args.session)
    result = agent.run(args.query)
    for event in result.events:
        if event.kind == "tool.call":
            print(f"[tool] {event.payload['name']} {event.payload.get('args')}")
        elif event.kind == "text.delta":
            print(event.payload["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
