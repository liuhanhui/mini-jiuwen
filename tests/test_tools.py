from pathlib import Path

import pytest

from mini_swarm.engine.tools import ToolError, ToolRegistry, make_default_tools


def test_read_file_strips_utf8_bom(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_bytes("\ufeffhello swarm\n".encode("utf-8"))
    tools = make_default_tools(tmp_path)

    result = tools.call("read_file", {"path": "README.md"})

    assert result.ok is True
    assert result.output.startswith("hello swarm")
    assert "\ufeff" not in result.output


def test_read_file_returns_workspace_content(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("hello swarm\n", encoding="utf-8")
    tools = make_default_tools(tmp_path)

    result = tools.call("read_file", {"path": "README.md"})

    assert result.ok is True
    assert "hello swarm" in result.output


def test_read_file_rejects_path_outside_workspace(tmp_path: Path) -> None:
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("nope", encoding="utf-8")
    tools = make_default_tools(tmp_path)

    with pytest.raises(ToolError, match="workspace"):
        tools.call("read_file", {"path": "../secret.txt"})


def test_write_file_creates_file_inside_workspace(tmp_path: Path) -> None:
    tools = make_default_tools(tmp_path)

    result = tools.call("write_file", {"path": "notes/a.txt", "content": "saved"})

    assert result.ok is True
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "saved"


def test_bash_runs_with_workspace_as_cwd(tmp_path: Path) -> None:
    tools = make_default_tools(tmp_path)

    result = tools.call(
        "bash",
        {
            "command": "python -c \"from pathlib import Path; Path('out.txt').write_text('ok', encoding='utf-8')\""
        },
    )

    assert result.ok is True
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "ok"


def test_unknown_tool_is_an_error(tmp_path: Path) -> None:
    tools = make_default_tools(tmp_path)

    with pytest.raises(ToolError, match="unknown"):
        tools.call("not_a_tool", {})


def test_tool_schemas_list_the_builtins(tmp_path: Path) -> None:
    tools = make_default_tools(tmp_path)
    names = {schema["name"] for schema in tools.schemas()}
    assert names == {"read_file", "write_file", "bash", "task", "ask_teammate"}
