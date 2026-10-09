from pathlib import Path

from mini_swarm.engine.session import Session


def test_session_roundtrip(tmp_path: Path) -> None:
    session = Session(session_id="s1", store_dir=tmp_path)
    session.add_user("hi")
    session.add_assistant("hello")
    session.save()

    loaded = Session.load(session_id="s1", store_dir=tmp_path)

    assert loaded.messages == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
