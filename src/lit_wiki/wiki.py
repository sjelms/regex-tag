from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from .bibliography import BibliographyIndex
from .config import AppConfig
from .models import BibliographyEntry, PersonRecord
from .notes import source_note_path


def _ensure_index(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "# Wiki Index\n\n"
        "## Overview\n"
        "- [Overview](overview.md) — living synthesis\n\n"
        "## Sources\n\n"
        "## Entities\n\n"
        "## Concepts\n"
    )


def update_index(config: AppConfig, entry: BibliographyEntry) -> None:
    index_path = config.wiki_dir / "index.md"
    content = _ensure_index(index_path)
    new_line = f"- [{entry.title}](sources/{entry.citekey}_wiki.md) — [@{entry.citekey}]"
    pattern = re.compile(rf"^- \[{re.escape(entry.title)}\]\(sources/{re.escape(entry.citekey)}_wiki\.md\).*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(new_line, content)
    elif "## Sources\n" in content:
        content = content.replace("## Sources\n", f"## Sources\n{new_line}\n")
    else:
        content += f"\n## Sources\n{new_line}\n"
    index_path.write_text(content, encoding="utf-8")


def update_entity_index(config: AppConfig, person: PersonRecord) -> None:
    index_path = config.wiki_dir / "index.md"
    content = _ensure_index(index_path)
    line = f"- [{person.display_name}](entities/{person.display_name}.md) — person"
    pattern = re.compile(
        rf"^- \[{re.escape(person.display_name)}\]\(entities/{re.escape(person.display_name)}\.md\).*$",
        re.MULTILINE,
    )
    if pattern.search(content):
        content = pattern.sub(line, content)
    elif "## Entities\n" in content:
        content = content.replace("## Entities\n", f"## Entities\n{line}\n")
    else:
        content += f"\n## Entities\n{line}\n"
    index_path.write_text(content, encoding="utf-8")


def update_log(config: AppConfig, entry: BibliographyEntry, action: str = "ingest") -> None:
    log_path = config.wiki_dir / "log.md"
    prefix = f"## [{date.today().isoformat()}] {action} | {entry.title} [@{entry.citekey}]"
    previous = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    log_path.write_text(prefix + "\n\n" + previous, encoding="utf-8")


def update_overview(config: AppConfig, bibliography: BibliographyIndex) -> None:
    overview_path = config.wiki_dir / "overview.md"
    source_paths = sorted(config.wiki_sources_dir.glob("*_wiki.md"))
    content = [
        "---",
        'title: "Overview"',
        "aliases: []",
        "see also: []",
        "tag: []",
        f'creation: "{date.today().isoformat()}"',
        f'modified: "{date.today().isoformat()}"',
        "---",
        "",
        "# Overview",
        "",
        f"Ingested source notes: {len(source_paths)}",
        "",
        "## Recently Ingested Sources",
    ]
    for path in source_paths[:10]:
        citekey = path.stem.removesuffix("_wiki")
        entry = bibliography.get(citekey)
        label = entry.title if entry else citekey
        content.append(f"- [[{path.stem}]] — {label}")
    overview_path.write_text("\n".join(content) + "\n", encoding="utf-8")


def ensure_person_pages(config: AppConfig, entry: BibliographyEntry) -> None:
    entities_dir = config.wiki_dir / "entities"
    entities_dir.mkdir(parents=True, exist_ok=True)
    for person in entry.authors + entry.editors:
        page_path = entities_dir / f"{person.display_name}.md"
        if not page_path.exists():
            page_path.write_text(
                "\n".join(
                    [
                        "---",
                        f'title: "{person.display_name}"',
                        'type: "entity"',
                        "tags: []",
                        f'sources: ["{entry.citekey}"]',
                        f'last_updated: "{date.today().isoformat()}"',
                        "---",
                        "",
                        f"# {person.display_name}",
                        "",
                        f"- Referenced by [[{entry.citekey}_wiki]]",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        update_entity_index(config, person)


def build_graph(config: AppConfig) -> tuple[int, int]:
    nodes: list[dict[str, str]] = []
    edges: list[dict[str, str]] = []
    wiki_files = list(config.wiki_dir.rglob("*.md"))
    id_set = {path.stem for path in wiki_files}
    for path in wiki_files:
        nodes.append({"id": path.stem, "path": str(path.relative_to(config.repo_root))})
        content = path.read_text(encoding="utf-8")
        for link in re.findall(r"\[\[([^\]]+)\]\]", content):
            if link in id_set and link != path.stem:
                edges.append({"from": path.stem, "to": link})
    graph_payload = {"nodes": nodes, "edges": edges, "built": date.today().isoformat()}
    config.graph_dir.mkdir(parents=True, exist_ok=True)
    (config.graph_dir / "graph.json").write_text(json.dumps(graph_payload, indent=2), encoding="utf-8")
    html = (
        "<html><body><h1>Literature Wiki Graph</h1><pre>"
        + json.dumps(graph_payload, indent=2)
        + "</pre></body></html>"
    )
    (config.graph_dir / "graph.html").write_text(html, encoding="utf-8")
    return len(nodes), len(edges)


def lint_wiki(config: AppConfig) -> str:
    source_files = list(config.wiki_sources_dir.glob("*_wiki.md"))
    broken_links: list[str] = []
    id_set = {path.stem for path in config.wiki_dir.rglob("*.md")}
    for path in config.wiki_dir.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for link in re.findall(r"\[\[([^\]]+)\]\]", content):
            if link.startswith("@"):
                continue
            if link not in id_set:
                broken_links.append(f"{path.name}: [[{link}]]")
    report = [
        "# Lint Report",
        "",
        f"- Source notes: {len(source_files)}",
        f"- Broken links: {len(broken_links)}",
    ]
    if broken_links:
        report.append("")
        report.append("## Broken Links")
        report.extend(f"- {item}" for item in broken_links)
    return "\n".join(report) + "\n"
