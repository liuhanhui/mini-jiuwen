from __future__ import annotations

import argparse
import asyncio
import os
import sys

from mini_swarm.doorbell.start import AGENTSERVER_PORT, start_processes
from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.llm import LlmError, OpenAICompatModel
from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.team import Team, make_team
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


def has_api_key() -> bool:
    return bool(os.environ.get("MINI_SWARM_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def resolve_runtime_model(workspace, *, demo: bool):
    if demo:
        return build_demo_model(workspace)
    return OpenAICompatModel.from_env()


def build_demo_agent(workspace, session_id: str, rail=None) -> Team:
    return make_team(
        workspace=workspace,
        model=resolve_runtime_model(workspace, demo=True),
        session_id=session_id,
        stop=StopPolicy(max_steps=8),
        rail_path=rail,
    )


def _drain(agent: DeepAgent):
    async def _run():
        return [event async for event in agent.attach_output()]

    return asyncio.run(_run())


def _print_events(events) -> None:
    for event in events:
        if event.kind == "tool.call":
            print(f"[tool] {event.payload['name']} {event.payload.get('args')}")
        elif event.kind == "context.compact":
            print(
                f"[compact] dropped={event.payload.get('dropped')} "
                f"kept={event.payload.get('kept')}"
            )
        elif event.kind == "text.delta":
            print(event.payload["text"])


def _serve(app, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mini JiuwenSwarm")
    parser.add_argument("query", nargs="?", default="What is the first line of README?")
    parser.add_argument("--demo", action="store_true", help="Use the scripted read_file model")
    parser.add_argument("--serve", action="store_true", help="Start the M2 HTTP doorbell")
    parser.add_argument("--start", action="store_true", help="Start Gateway + AgentServer (M3)")
    parser.add_argument("--role", choices=["agentserver", "gateway"], help="Run one M3 process")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument(
        "--agentserver-url",
        default=f"ws://127.0.0.1:{AGENTSERVER_PORT}/e2a",
    )
    parser.add_argument("--session", default="default")
    parser.add_argument("--rail", default=None, help="Path to rail.yaml (M5)")
    args = parser.parse_args(argv)
    _configure_stdio()

    needs_model = args.role != "gateway"
    if needs_model and not args.demo and not has_api_key():
        print(
            "Pass --demo for the scripted model, or set MINI_SWARM_API_KEY "
            "(OpenAI-compatible).",
            file=sys.stderr,
        )
        return 2

    workspace = resolve_workspace()
    if args.start:
        return start_processes(demo=args.demo, host=args.host, rail=args.rail)

    if args.role == "gateway":
        from mini_swarm.doorbell.gateway import create_gateway_app
        from mini_swarm.doorbell.start import GATEWAY_PORT

        _serve(
            create_gateway_app(agentserver_url=args.agentserver_url),
            args.host,
            args.port or GATEWAY_PORT,
        )
        return 0

    try:
        model = resolve_runtime_model(workspace, demo=args.demo)
    except LlmError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.role == "agentserver":
        from mini_swarm.doorbell.agentserver import create_agentserver_app

        _serve(
            create_agentserver_app(
                workspace=workspace,
                model=model,
                rail_path=args.rail,
            ),
            args.host,
            args.port or AGENTSERVER_PORT,
        )
        return 0

    if args.serve:
        from mini_swarm.doorbell.http import create_app

        _serve(
            create_app(
                workspace=workspace,
                model=model,
                rail_path=args.rail,
            ),
            args.host,
            args.port or 8765,
        )
        return 0

    agent = make_team(
        workspace=workspace,
        model=model,
        session_id=args.session,
        stop=StopPolicy(max_steps=8),
        rail_path=args.rail,
    )
    agent.send_input(args.query)
    _print_events(_drain(agent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
