from __future__ import annotations

import os
from pathlib import Path

from mini_swarm.engine.tools import BUILTIN_TOOL_NAMES, ToolRegistry


class RailError(Exception):
    pass


def load_enabled_tools(path: Path) -> list[str]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RailError("PyYAML is required to load rail.yaml") from exc
    raw = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "tools" not in data:
        raise RailError("rail.yaml must define a tools list")
    items = data.get("tools")
    if not isinstance(items, list):
        raise RailError("rail.yaml tools must be a list")
    names: list[str] = []
    for item in items:
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict) and item.get("name"):
            name = str(item["name"])
        else:
            raise RailError("each rail tool must be a name")
        if name not in BUILTIN_TOOL_NAMES:
            raise RailError(f"unknown tool in rail: {name}")
        if name not in names:
            names.append(name)
    return names


def resolve_rail_path(workspace: Path, rail_path: str | Path | None = None) -> Path | None:
    if rail_path:
        return Path(rail_path)
    env = os.environ.get("MINI_SWARM_RAIL")
    if env:
        return Path(env)
    candidate = Path(workspace) / "rail.yaml"
    return candidate if candidate.is_file() else None


def make_rail_tools(
    workspace: Path,
    rail_path: str | Path | None = None,
) -> ToolRegistry:
    path = resolve_rail_path(workspace, rail_path)
    if path is None:
        return ToolRegistry(workspace)
    enabled = load_enabled_tools(path)
    return ToolRegistry(workspace, enabled=enabled)
