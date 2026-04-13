from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import yaml

from .bibliography import BibliographyIndex, parse_bibliography
from .config import AppConfig
from .models import BibliographyEntry, PersonRecord
from .notes import source_note_path
from .utils import year_as_int


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


def update_concept_index(config: AppConfig, concept_name: str) -> None:
    index_path = config.wiki_dir / "index.md"
    content = _ensure_index(index_path)
    line = f"- [{concept_name}](concepts/{concept_name}.md) — concept"
    pattern = re.compile(
        rf"^- \[{re.escape(concept_name)}\]\(concepts/{re.escape(concept_name)}\.md\).*$",
        re.MULTILINE,
    )
    if pattern.search(content):
        content = pattern.sub(line, content)
    elif "## Concepts\n" in content:
        content = content.replace("## Concepts\n", f"## Concepts\n{line}\n")
    else:
        content += f"\n## Concepts\n{line}\n"
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


def ensure_concept_pages(config: AppConfig, entry: BibliographyEntry, sections: dict[str, object]) -> None:
    concepts_dir = config.wiki_dir / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    for raw_link in sections.get("see_also_links", []):
        concept_name = str(raw_link).strip().replace("[[", "").replace("]]", "")
        if not concept_name or concept_name.startswith("@") or concept_name.endswith("_wiki"):
            continue
        page_path = concepts_dir / f"{concept_name}.md"
        if not page_path.exists():
            page_path.write_text(
                "\n".join(
                    [
                        "---",
                        f'title: "{concept_name}"',
                        'type: "concept"',
                        "tags: []",
                        f'sources: ["{entry.citekey}"]',
                        f'last_updated: "{date.today().isoformat()}"',
                        "---",
                        "",
                        f"# {concept_name}",
                        "",
                        f"- Referenced by [[{entry.citekey}_wiki]]",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        update_concept_index(config, concept_name)


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
    raw_sources_in_wiki: list[str] = []
    broken_citekeys: list[str] = []
    future_references: list[str] = []
    suspicious_metadata: list[str] = []
    extraction_artifacts: list[str] = []
    id_set = {path.stem for path in config.wiki_dir.rglob("*.md")}
    bibliography = BibliographyIndex({}) if not config.bibliography_file.exists() else parse_bibliography(config.bibliography_file)

    for path in config.wiki_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pdf", ".epub", ".xhtml", ".html"}:
            raw_sources_in_wiki.append(str(path.relative_to(config.repo_root)))
        elif (
            path.suffix.lower() in {".md", ".markdown"}
            and not path.name.endswith("_wiki.md")
            and path.parent == config.wiki_sources_dir
        ):
            raw_sources_in_wiki.append(str(path.relative_to(config.repo_root)))

    for path in config.wiki_dir.rglob("*.md"):
        if path.name == "lint-report.md":
            continue
        content = path.read_text(encoding="utf-8")
        for link in re.findall(r"\[\[([^\]]+)\]\]", content):
            if link.startswith("@"):
                citekey = link.removeprefix("@")
                if citekey in {"article", "book", "report", "misc", "inproceedings", "phdthesis", "mastersthesis", "thesis"}:
                    continue
                if bibliography.get(citekey) is None:
                    broken_citekeys.append(f"{path.name}: [[{link}]]")
                continue
            if link not in id_set:
                broken_links.append(f"{path.name}: [[{link}]]")

        if path.name.endswith("_wiki.md") and content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                tag_count = len(frontmatter.get("tag") or [])
                see_also_count = len(frontmatter.get("see also") or [])
                if tag_count > 12 or see_also_count > 5:
                    suspicious_metadata.append(f"{path.name}: tag={tag_count}, see also={see_also_count}")

                source_year = year_as_int(str(frontmatter.get("year", "")))
                related_section = content.split("# Related References", 1)[1] if "# Related References" in content else ""
                for citekey in re.findall(r"\[\[@([A-Za-z0-9:-]+)\]\]", related_section):
                    candidate = bibliography.get(citekey)
                    if candidate is None:
                        broken_citekeys.append(f"{path.name}: [[@{citekey}]]")
                        continue
                    candidate_year = year_as_int(candidate.year)
                    if source_year and candidate_year and candidate_year > source_year:
                        future_references.append(f"{path.name}: [[@{citekey}]] ({candidate.year} > {source_year})")

    for path in config.extracted_dir.glob("*.md"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        if "\x00" in content or "This content downloaded from" in content:
            extraction_artifacts.append(str(path.relative_to(config.repo_root)))

    report = [
        "# Lint Report",
        "",
        f"- Source notes: {len(source_files)}",
        f"- Broken links: {len(broken_links)}",
        f"- Broken bibliography links: {len(broken_citekeys)}",
        f"- Raw sources under wiki/: {len(raw_sources_in_wiki)}",
        f"- Future-dated references: {len(future_references)}",
        f"- Suspicious metadata blocks: {len(suspicious_metadata)}",
        f"- Extraction artifacts: {len(extraction_artifacts)}",
    ]
    if broken_links:
        report.append("")
        report.append("## Broken Links")
        report.extend(f"- {item}" for item in broken_links)
    if broken_citekeys:
        report.append("")
        report.append("## Broken Bibliography Links")
        report.extend(f"- {item}" for item in broken_citekeys)
    if raw_sources_in_wiki:
        report.append("")
        report.append("## Raw Sources Under Wiki")
        report.extend(f"- {item}" for item in raw_sources_in_wiki)
    if future_references:
        report.append("")
        report.append("## Future-Dated References")
        report.extend(f"- {item}" for item in future_references)
    if suspicious_metadata:
        report.append("")
        report.append("## Suspicious Metadata")
        report.extend(f"- {item}" for item in suspicious_metadata)
    if extraction_artifacts:
        report.append("")
        report.append("## Extraction Artifacts")
        report.extend(f"- {item}" for item in extraction_artifacts)
    return "\n".join(report) + "\n"
