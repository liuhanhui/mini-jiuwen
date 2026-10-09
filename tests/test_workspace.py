from pathlib import Path

from mini_swarm.workspace import resolve_workspace


def test_uses_env_when_writable(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "ws"
    monkeypatch.setenv("MINI_SWARM_WORKSPACE", str(target))
    path = resolve_workspace()
    assert path == target.resolve()
    assert path.is_dir()


def test_falls_back_when_preferred_is_not_writable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINI_SWARM_WORKSPACE", str(tmp_path / "blocked"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr("mini_swarm.workspace.can_create_dir", lambda _path: False)

    path = resolve_workspace()

    assert path == (tmp_path / "home" / ".mini-swarm" / "tasks").resolve()
    assert path.is_dir()
