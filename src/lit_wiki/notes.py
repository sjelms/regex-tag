from __future__ import annotations

from datetime import date
from pathlib import Path

from .models import BibliographyEntry, SourceRecord
from .utils import dedupe_casefold


def source_note_path(base_dir: Path, citekey: str) -> Path:
    return base_dir / f"{citekey}_wiki.md"


def _yaml_line(key: str, value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'{key}: "{escaped}"'


def _list_block(key: str, values: list[str]) -> list[str]:
    if not values:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for value in values:
        escaped = value.replace('"', '\\"')
        lines.append(f'  - "{escaped}"')
    return lines


def _person_lines(prefix: str, people: list[str]) -> list[str]:
    return [_yaml_line(f"{prefix} - {index}", person) for index, person in enumerate(people, start=1)]


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def render_note(
    entry: BibliographyEntry,
    source_record: SourceRecord,
    sections: dict[str, object],
    existing_note: str | None = None,
) -> str:
    today = date.today().isoformat()
    creation = today
    if existing_note and existing_note.startswith("---"):
        parts = existing_note.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if line.startswith("creation:"):
                    creation = line.split(":", 1)[1].strip().strip('"')
                    break

    author_values = [person.wiki_link for person in entry.authors]
    editor_values = [person.wiki_link for person in entry.editors]
    if not author_values and not editor_values:
        author_values = ["[[Unknown Author]]"]
    see_also_links = [f"[[{entry.citekey}_wiki]]"]
    for link in _string_list(sections.get("see_also_links", [])):
        if link not in see_also_links:
            see_also_links.append(str(link))
    tag_values = dedupe_casefold(list(entry.keywords))
    for tag in _string_list(sections.get("keyword_tags", [])):
        if tag not in tag_values:
            tag_values.append(str(tag))
    tag_values = dedupe_casefold(tag_values)

    yaml_lines = [
        "---",
        _yaml_line("title", entry.title),
        _yaml_line("year", entry.year),
        _yaml_line("key", f"[[@{entry.citekey}]]"),
    ]
    if entry.entry_type:
        yaml_lines.append(_yaml_line("type", f"[[@{entry.entry_type}]]"))
    yaml_lines.extend(_person_lines("author", author_values))
    yaml_lines.extend(_person_lines("editor", editor_values))
    yaml_lines.extend(_list_block("aliases", []))
    yaml_lines.extend(_list_block("see also", see_also_links))
    yaml_lines.extend(_list_block("tag", tag_values))
    yaml_lines.append(_yaml_line("creation", creation))
    yaml_lines.append(_yaml_line("modified", today))
    yaml_lines.append("---")

    related_references = []
    for citekey in _string_list(sections.get("related_references", [])):
        cleaned = citekey.replace("[[@", "").replace("]]", "").replace("@", "").strip()
        if cleaned:
            related_references.append(f"- [[@{cleaned}]]")

    body_lines = [
        "",
        "### Summary of Key Points",
        *[f"- {item}" for item in _string_list(sections.get("summary_points", []))],
        "",
        "### Questions:",
        *[f"- {item}" for item in _string_list(sections.get("questions", []))],
        "",
        "### Notes:",
        *[f"- {item}" for item in _string_list(sections.get("notes", []))],
        "",
        "---",
        "",
        "",
        "# Abstract",
        "",
        str(sections.get("abstract", "")).strip(),
        "",
        "---",
        "",
        "## Cross-reference Bibliography",
        "",
        *_string_list(sections.get("cross_reference_bibliography", [])),
        "",
        "---",
        "",
        "# Background",
        "> [!prompt]What was the context for this research?",
        ">What has been studied or determined already?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("background", []))],
        "",
        "---",
        "",
        "# Methods & Nature of this Study",
        "> [!prompt] What was the objective?",
        ">How did the author(s) collect data?",
        ">When and where did the research take place?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("methods", []))],
        "",
        "---",
        "",
        "# Results",
        "> [!prompt] What highlights emerged?",
        ">Were there any surprises?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("results", []))],
        "",
        "---",
        "",
        "# Data",
        "> [!prompt] What is most striking about the tables, graphs, illustrations?",
        ">Why did the author(s) include them?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("data", []))],
        "",
        "---",
        "",
        "# Conclusions",
        "> [!prompt] What did the author(s) learn overall?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("conclusions", []))],
        "",
        "---",
        "",
        "# Next Steps",
        "> [!prompt] What is implied or proposed for future study?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("next_steps", []))],
        "",
        "---",
        "",
        "# Significance",
        "> [!prompt] Why does this research matter?",
        "",
        *[f"- {item}" for item in _string_list(sections.get("significance", []))],
        "",
        "---",
        "",
        "# Related References",
        "> [!prompt] any cited papers in the original that also match a Bibliography entry.",
        "",
        *(related_references or ["- No bibliography-matched cited references found yet."]),
        "",
    ]
    return "\n".join(yaml_lines + body_lines)
