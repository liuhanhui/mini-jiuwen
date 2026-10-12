from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

AGENTSERVER_PORT = 18765
GATEWAY_PORT = 8764


def _src_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def child_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base if base is not None else os.environ)
    src = str(_src_dir())
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not existing else f"{src}{os.pathsep}{existing}"
    return env


def build_start_commands(
    *,
    demo: bool,
    host: str = "127.0.0.1",
) -> list[list[str]]:
    prefix = [sys.executable, "-m", "mini_swarm.cli"]
    if demo:
        prefix.append("--demo")
    agentserver = prefix + [
        "--role",
        "agentserver",
        "--host",
        host,
        "--port",
        str(AGENTSERVER_PORT),
    ]
    gateway = prefix + [
        "--role",
        "gateway",
        "--host",
        host,
        "--port",
        str(GATEWAY_PORT),
        "--agentserver-url",
        f"ws://{host}:{AGENTSERVER_PORT}/e2a",
    ]
    return [agentserver, gateway]


def start_processes(*, demo: bool, host: str = "127.0.0.1") -> int:
    commands = build_start_commands(demo=demo, host=host)
    env = child_env()
    procs = [subprocess.Popen(cmd, env=env) for cmd in commands]
    try:
        procs[-1].wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
    return 0
