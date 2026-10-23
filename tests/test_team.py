from pathlib import Path

from mini_swarm.engine.deep_agent import DeepAgent
from mini_swarm.engine.model import ModelTurn, ScriptedModel, ToolCall
from mini_swarm.engine.session import Session
from mini_swarm.engine.stop import StopPolicy
from mini_swarm.engine.team import Team, make_team


def test_team_is_two_agent_objects_in_one_process(tmp_path: Path) -> None:
    model = ScriptedModel([ModelTurn(text="unused")])
    team = make_team(
        workspace=tmp_path,
        model=model,
        session_id="s1",
        stop=StopPolicy(max_steps=8),
    )
    assert isinstance(team, Team)
    assert isinstance(team.leader, DeepAgent)
    assert isinstance(team.teammate, DeepAgent)
    assert team.leader is not team.teammate
    assert team.leader.session.session_id == "s1"
    assert team.teammate.session.session_id == "s1-teammate"


def test_leader_ask_teammate_reuses_the_same_teammate_session(tmp_path: Path) -> None:
    model = ScriptedModel(
        [
            ModelTurn(
                tool_calls=[
                    ToolCall(
                        id="a1",
                        name="ask_teammate",
                        args={"prompt": "remember apple"},
                    )
                ]
            ),
            ModelTurn(text="got apple"),
            ModelTurn(text="leader stored apple"),
            ModelTurn(
                tool_calls=[
                    ToolCall(
                        id="a2",
                        name="ask_teammate",
                        args={"prompt": "what did I say?"},
                    )
                ]
            ),
            ModelTurn(text="you said apple"),
            ModelTurn(text="leader heard you said apple"),
        ]
    )
    team = make_team(
        workspace=tmp_path,
        model=model,
        session_id="s1",
        stop=StopPolicy(max_steps=8),
    )

    first = team.leader._react.run("ask once")
    second = team.leader._react.run("ask again")

    assert first.final_text == "leader stored apple"
    assert second.final_text == "leader heard you said apple"
    loaded = Session.load("s1-teammate", tmp_path / "sessions")
    contents = [msg.get("content") for msg in loaded.messages]
    assert "remember apple" in contents
    assert "what did I say?" in contents
    assert loaded.messages[0]["content"] != "ask once"


def test_teammate_does_not_get_ask_teammate_tool(tmp_path: Path) -> None:
    team = make_team(
        workspace=tmp_path,
        model=ScriptedModel([ModelTurn(text="unused")]),
        session_id="s1",
        stop=StopPolicy(max_steps=8),
    )
    assert "ask_teammate" in team.leader._react.tools.names()
    assert "ask_teammate" not in team.teammate._react.tools.names()
