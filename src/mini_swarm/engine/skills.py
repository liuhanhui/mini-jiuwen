from __future__ import annotations

from pathlib import Path


def _first_line(text: str) -> str:
    for line in text.splitlines():
        title = line.strip().lstrip("#").strip()
        if title:
            return title
    return ""


def list_skills(workspace: Path) -> list[tuple[str, str, str]]:
    root = Path(workspace) / "skills"
    if not root.is_dir():
        return []
    items: list[tuple[str, str, str]] = []
    for child in sorted(root.iterdir()):
        skill = child / "SKILL.md"
        if not child.is_dir() or not skill.is_file():
            continue
        title = _first_line(skill.read_text(encoding="utf-8-sig"))
        if not title:
            continue
        items.append((child.name, title, f"skills/{child.name}/SKILL.md"))
    return items


def load_skill_catalog_messages(workspace: Path) -> list[dict]:
    items = list_skills(workspace)
    if not items:
        return []
    lines = [
        "# Skills",
        "On-demand procedures. Use read_file on the path when you need the full steps.",
    ]
    for name, title, rel in items:
        lines.append(f"- {name}: {title}")
        lines.append(f"  path: {rel}")
    return [{"role": "system", "content": "\n".join(lines)}]
