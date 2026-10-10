from __future__ import annotations

import argparse
import asyncio
import sys

from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.tools import make_default_tools
from mini_swarm.workspace import resolve_workspace


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def build_demo_model(workspace) -> ScriptedModel:
    readme = workspace / "README.md"
    if not readme.exists():
        readme.write_text("hello from mini-swarm\n", encoding="utf-8")
    first_line = readme.read_text(encoding="utf-8-sig").splitlines()[0]
    return ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(id="c1", name="read_file", args={"path": "README.md"})
                ]
            ),
            ModelTurn(text=f"README starts with: {first_line}"),
        ]
    )


def build_demo_agent(workspace, session_id: str) -> DeepAgent:
    return DeepAgent(
        model=build_demo_model(workspace),
        tools=make_default_tools(workspace),
        session=Session(session_id=session_id, store_dir=workspace / "sessions"),
        stop=StopPolicy(max_steps=8),
    )


def _drain(agent: DeepAgent):
    async def _run():
        return [event async for event in agent.attach_output()]

    return asyncio.run(_run())


def _print_events(events) -> None:
    for event in events:
        if event.kind == "tool.call":
            print(f"[tool] {event.payload['name']} {event.payload.get('args')}")
        elif event.kind == "text.delta":
            print(event.payload["text"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mini JiuwenSwarm")
    parser.add_argument("query", nargs="?", default="What is the first line of README?")
    parser.add_argument("--demo", action="store_true", help="Use the scripted read_file model")
    parser.add_argument("--serve", action="store_true", help="Start the HTTP doorbell (M2)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--session", default="default")
    args = parser.parse_args(argv)
    _configure_stdio()

    if not args.demo:
        print(
            "Pass --demo to use the scripted model "
            "(or --serve --demo for the HTTP doorbell).",
            file=sys.stderr,
        )
        return 2

    workspace = resolve_workspace()
    if args.serve:
        import uvicorn

        from mini_swarm.doorbell.http import create_app

        app = create_app(workspace=workspace, model=build_demo_model(workspace))
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    agent = build_demo_agent(workspace, args.session)
    agent.send_input(args.query)
    _print_events(_drain(agent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
