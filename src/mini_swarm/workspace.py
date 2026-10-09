from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("mini_swarm")


def can_create_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve_workspace() -> Path:
    raw = os.environ.get("MINI_SWARM_WORKSPACE")
    preferred = Path(raw) if raw else Path.cwd() / "workspace"
    if can_create_dir(preferred):
        return preferred.resolve()

    fallback = Path.home() / ".mini-swarm" / "tasks"
    fallback.mkdir(parents=True, exist_ok=True)
    logger.warning(
        "workspace %s is not writable, falling back to %s",
        preferred,
        fallback,
    )
    return fallback.resolve()
