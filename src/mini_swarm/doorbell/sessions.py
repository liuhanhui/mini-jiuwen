from __future__ import annotations

from pathlib import Path

from mini_swarm.engine.session import Session


def open_session(session_id: str, store_dir: Path) -> Session:
    if (store_dir / f"{session_id}.json").exists():
        return Session.load(session_id, store_dir)
    return Session(session_id=session_id, store_dir=store_dir)
