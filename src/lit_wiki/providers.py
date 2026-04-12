from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .bibliography import BibliographyIndex
from .config import AppConfig
from .models import BibliographyEntry
from .utils import bullet_list, ensure_suffix_link


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _extract_references(extracted_text: str, bibliography: BibliographyIndex, current_citekey: str) -> list[str]:
    references: list[str] = []
    lowered = extracted_text.lower()
    for citekey, entry in bibliography.entries.items():
        if citekey == current_citekey:
            continue
        title = entry.title.strip()
        if not title:
            continue
        title_lower = title.lower()
        if title_lower in lowered:
            references.append(citekey)
            continue
        if entry.doi and entry.doi.lower() in lowered:
            references.append(citekey)
    return sorted(dict.fromkeys(references))


def heuristic_sections(
    entry: BibliographyEntry,
    extracted_text: str,
    bibliography: BibliographyIndex,
) -> dict[str, object]:
    abstract_source = _first_non_empty(entry.abstract, extracted_text)
    highlights = bullet_list(abstract_source, count=3) or ["Summary pending manual review."]
    questions = [
        f"How does [[@{entry.citekey}]] relate to adjacent literature in this area?",
        "Which claims or methods need closer verification from the full text?",
    ]
    notes = [
        f"Generated from bibliography-linked source note for [@{entry.citekey}].",
        f"Primary note target: {ensure_suffix_link(entry.citekey)}",
    ]
    methods_source = _first_non_empty(extracted_text, entry.abstract)
    related_citekeys = _extract_references(extracted_text, bibliography, entry.citekey)
    cross_refs = bibliography.same_author_entries(entry.citekey)

    return {
        "summary_points": highlights,
        "questions": questions,
        "notes": notes,
        "abstract": _first_non_empty(entry.abstract, "Abstract not available in BibTeX; generated from extracted content."),
        "cross_reference_bibliography": [
            f"- [[@{related.citekey}]] — {related.title}" for related in cross_refs
        ] or ["- No local bibliography cross-references found yet."],
        "background": bullet_list(_first_non_empty(entry.abstract, extracted_text), count=3)
        or ["Background requires manual review."],
        "methods": bullet_list(methods_source, count=3) or ["Method details require manual review."],
        "results": bullet_list(extracted_text, count=3) or ["Results require manual review."],
        "data": ["Data tables and figures require manual review from the source artifact."],
        "conclusions": bullet_list(_first_non_empty(entry.abstract, extracted_text), count=2)
        or ["Conclusions require manual review."],
        "next_steps": ["Review the full source for follow-on studies or recommendations."],
        "significance": [
            f"This source matters within the local literature graph around [[@{entry.citekey}]]."
        ],
        "related_references": related_citekeys,
    }


def _openai_compatible_sections(
    config: AppConfig,
    entry: BibliographyEntry,
    extracted_text: str,
) -> dict[str, object]:
    api_key = os.getenv(config.provider_api_key_env, "")
    if not config.provider_api_base:
        raise RuntimeError("Provider API base is not configured.")

    prompt = {
        "title": entry.title,
        "citekey": entry.citekey,
        "abstract": entry.abstract,
        "content": extracted_text[:15000],
        "task": "Return JSON with keys summary_points, questions, notes, background, methods, results, data, conclusions, next_steps, significance.",
    }
    payload = json.dumps(
        {
            "model": config.provider_model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url=config.provider_api_base.rstrip("/") + "/chat/completions",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
        data=payload,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.provider_timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_sections(
    config: AppConfig,
    entry: BibliographyEntry,
    extracted_text: str,
    bibliography: BibliographyIndex,
) -> tuple[dict[str, object], str]:
    backend = config.provider_backend.lower()
    if backend in {"heuristic", ""}:
        return heuristic_sections(entry, extracted_text, bibliography), "heuristic"
    if backend in {"lm_studio", "openai_compatible", "openai"}:
        try:
            sections = _openai_compatible_sections(config, entry, extracted_text)
            sections["related_references"] = _extract_references(extracted_text, bibliography, entry.citekey)
            return sections, backend
        except (RuntimeError, urllib.error.URLError, KeyError, json.JSONDecodeError):
            return heuristic_sections(entry, extracted_text, bibliography), "heuristic-fallback"
    if backend == "gemini":
        return heuristic_sections(entry, extracted_text, bibliography), "heuristic-fallback"
    return heuristic_sections(entry, extracted_text, bibliography), "heuristic"

