from mini_swarm.engine.stop import StopPolicy


def test_stop_after_max_steps() -> None:
    policy = StopPolicy(max_steps=3)
    assert policy.should_stop(step=3, has_final_text=False) is True
    assert policy.should_stop(step=2, has_final_text=False) is False


def test_stop_when_model_returns_final_text() -> None:
    policy = StopPolicy(max_steps=10)
    assert policy.should_stop(step=1, has_final_text=True) is True
