from pathlib import Path

from mini_swarm.cli import main


def test_demo_cli_reads_readme_and_prints_answer(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("MINI_SWARM_WORKSPACE", str(tmp_path))
    (tmp_path / "README.md").write_text("first line\n", encoding="utf-8")

    code = main(["--demo"])

    captured = capsys.readouterr()
    assert code == 0
    assert "[tool] read_file" in captured.out
    assert "first line" in captured.out


def test_cli_without_demo_exits_with_help(capsys) -> None:
    code = main(["what is in README?"])
    captured = capsys.readouterr()
    assert code == 2
    assert "--demo" in captured.err
