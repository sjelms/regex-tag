from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .bibliography import BibliographyIndex
from .budget import can_spend, estimate_usage, load_budget_ledger, record_spend
from .config import AppConfig, ProviderSpec
from .keywords import enrich_keywords, load_keyword_catalogue
from .models import ApprovalRequest, BibliographyEntry, GenerationOutcome
from .utils import bullet_list, ensure_suffix_link

REQUIRED_SECTION_KEYS = {
    "summary_points",
    "questions",
    "notes",
    "abstract",
    "cross_reference_bibliography",
    "background",
    "methods",
    "results",
    "data",
    "conclusions",
    "next_steps",
    "significance",
}


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
        if title.lower() in lowered:
            references.append(citekey)
            continue
        if entry.doi and entry.doi.lower() in lowered:
            references.append(citekey)
    return sorted(dict.fromkeys(references))


def _keyword_guidance(keyword_targets: list[str], max_terms: int) -> list[str]:
    return keyword_targets[:max_terms]


def heuristic_sections(
    entry: BibliographyEntry,
    extracted_text: str,
    bibliography: BibliographyIndex,
    keyword_targets: list[str],
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
    if keyword_targets:
        notes.append("Controlled vocabulary guidance: " + ", ".join(keyword_targets[:8]))
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


def _chunk_text(text: str, max_chars: int, max_requests: int) -> list[str]:
    if not text:
        return [""]
    if max_chars <= 0:
        return [text]
    chunks = [text[index:index + max_chars] for index in range(0, len(text), max_chars)]
    return chunks[:max_requests]


def _openai_compatible_request(provider: ProviderSpec, api_key: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url=provider.api_base.rstrip("/") + "/chat/completions",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=provider.timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str):
        raise json.JSONDecodeError("Provider response content is not text.", str(content), 0)

    candidates = [content.strip()]
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("Unable to parse JSON from provider response.", content, 0)


def _run_openai_compatible(
    provider: ProviderSpec,
    config: AppConfig,
    entry: BibliographyEntry,
    extracted_text: str,
    keyword_targets: list[str],
) -> dict[str, object]:
    api_key = os.getenv(provider.api_key_env, "")
    if not provider.api_base:
        raise RuntimeError(f"Provider '{provider.name}' API base is not configured.")

    chunks = _chunk_text(
        extracted_text,
        config.budget_policy.max_input_chars_per_request,
        config.budget_policy.max_requests_per_file,
    )
    if not chunks:
        chunks = [""]

    chunk_summaries: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        payload = {
            "model": provider.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "Return strict JSON only."},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Summarize this chunk into JSON with key `bullet_points` as a list of concise bullets.",
                            "title": entry.title,
                            "citekey": entry.citekey,
                            "chunk_index": index,
                            "keyword_guidance": _keyword_guidance(keyword_targets, config.keyword_policy.max_guidance_terms),
                            "content": chunk,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        result = _openai_compatible_request(provider, api_key, payload)
        bullets = result.get("bullet_points") or []
        if not isinstance(bullets, list) or not bullets:
            raise RuntimeError(f"Provider '{provider.name}' returned no bullet_points.")
        chunk_summaries.extend(str(item).strip() for item in bullets if str(item).strip())

    combined = "\n".join(chunk_summaries[:12])
    final_payload = {
        "model": provider.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": (
                            "Using the source metadata and chunk summaries, return JSON with keys "
                            "summary_points, questions, notes, abstract, background, methods, results, "
                            "data, conclusions, next_steps, significance."
                        ),
                        "title": entry.title,
                        "citekey": entry.citekey,
                        "abstract": entry.abstract,
                        "keyword_guidance": _keyword_guidance(keyword_targets, config.keyword_policy.max_guidance_terms),
                        "chunk_summaries": chunk_summaries[:12],
                        "combined_summary": combined,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    return _openai_compatible_request(provider, api_key, final_payload)


def _run_provider(
    provider: ProviderSpec,
    config: AppConfig,
    entry: BibliographyEntry,
    extracted_text: str,
    bibliography: BibliographyIndex,
    keyword_targets: list[str],
) -> dict[str, object]:
    backend = provider.backend.lower()
    if backend == "heuristic":
        return heuristic_sections(entry, extracted_text, bibliography, keyword_targets)
    if backend in {"lm_studio", "openai_compatible", "openai", "gemini"}:
        return _run_openai_compatible(provider, config, entry, extracted_text, keyword_targets)
    raise RuntimeError(f"Unsupported provider backend: {provider.backend}")


def _validate_sections(sections: dict[str, object]) -> tuple[bool, str]:
    missing = [key for key in REQUIRED_SECTION_KEYS if key not in sections]
    if missing:
        return False, f"missing required keys: {', '.join(sorted(missing))}"
    summary_points = sections.get("summary_points")
    if not isinstance(summary_points, list) or not summary_points:
        return False, "summary_points empty or invalid"
    abstract = str(sections.get("abstract", "")).strip()
    if not abstract:
        return False, "abstract empty"
    return True, ""


def _apply_keyword_enrichment(
    sections: dict[str, object],
    keyword_targets: list[str],
    keyword_tags: list[str],
) -> dict[str, object]:
    enriched = dict(sections)
    existing_links = [str(item) for item in enriched.get("see_also_links", [])]
    for target in keyword_targets:
        link = f"[[{target}]]"
        if link not in existing_links:
            existing_links.append(link)
    enriched["see_also_links"] = existing_links
    enriched["keyword_tags"] = list(dict.fromkeys(keyword_tags))
    return enriched


def _normalize_sections(
    sections: dict[str, object],
    entry: BibliographyEntry,
    bibliography: BibliographyIndex,
    extracted_text: str,
) -> dict[str, object]:
    normalized = dict(sections)
    if "cross_reference_bibliography" not in normalized:
        cross_refs = bibliography.same_author_entries(entry.citekey)
        normalized["cross_reference_bibliography"] = [
            f"- [[@{related.citekey}]] — {related.title}" for related in cross_refs
        ] or ["- No local bibliography cross-references found yet."]
    if "related_references" not in normalized:
        normalized["related_references"] = _extract_references(extracted_text, bibliography, entry.citekey)
    return normalized


def generate_sections(
    config: AppConfig,
    entry: BibliographyEntry,
    extracted_text: str,
    bibliography: BibliographyIndex,
    current_daily_tokens: int = 0,
) -> GenerationOutcome:
    catalogue = load_keyword_catalogue(config)
    keyword_targets, keyword_tags = enrich_keywords(
        extracted_text,
        catalogue,
        max_links=config.keyword_policy.max_see_also_links,
    )

    last_reason = "unknown provider failure"
    for _attempt in range(1, max(1, config.retry_policy.local_max_attempts) + 1):
        attempt_number = _attempt
        try:
            sections = _run_provider(
                config.primary_provider,
                config,
                entry,
                extracted_text,
                bibliography,
                keyword_targets,
            )
            sections = _normalize_sections(sections, entry, bibliography, extracted_text)
            valid, reason = _validate_sections(sections)
            if not valid:
                last_reason = reason
                continue
            sections = _apply_keyword_enrichment(sections, keyword_targets, keyword_tags)
            usage = estimate_usage(
                config.primary_provider.name,
                config.primary_provider.model,
                extracted_text,
                config.budget_policy,
            )
            return GenerationOutcome(
                status="success",
                sections=sections,
                provider_name=config.primary_provider.name,
                provider_model=config.primary_provider.model,
                usage=usage,
                keyword_targets=keyword_targets,
                keyword_tags=keyword_tags,
                local_attempts=attempt_number,
            )
        except (RuntimeError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            last_reason = str(exc)

    if not config.fallback_providers:
        sections = _apply_keyword_enrichment(
            heuristic_sections(entry, extracted_text, bibliography, keyword_targets),
            keyword_targets,
            keyword_tags,
        )
        usage = estimate_usage("heuristic", "heuristic", extracted_text, config.budget_policy)
        return GenerationOutcome(
            status="success",
            sections=sections,
            provider_name="heuristic",
            provider_model="heuristic",
            usage=usage,
            escalation_reason=last_reason,
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
            local_attempts=max(1, config.retry_policy.local_max_attempts),
        )

    ledger = load_budget_ledger(config.budget_ledger_file)
    for fallback in config.fallback_providers:
        usage = estimate_usage(fallback.name, fallback.model, extracted_text, config.budget_policy)
        allowed, denial_reason = can_spend(ledger, usage, config.budget_policy)
        if not allowed:
            return GenerationOutcome(
                status="needs_review",
                sections=None,
                provider_name=config.primary_provider.name,
                provider_model=config.primary_provider.model,
            usage=usage,
            escalation_reason=denial_reason,
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
            local_attempts=max(1, config.retry_policy.local_max_attempts),
        )
        approval = ApprovalRequest(
            citekey=entry.citekey,
            source_name=entry.title,
            reason=last_reason,
            primary_model=config.primary_provider.model,
            fallback_provider=fallback.name,
            fallback_model=fallback.model,
            estimated_chunk_count=usage.requests_made,
            usage=usage,
            current_daily_tokens=current_daily_tokens or ledger.get("total_tokens", 0),
            max_daily_tokens=config.budget_policy.max_tokens_per_day,
        )
        return GenerationOutcome(
            status="needs_approval",
            sections=None,
            provider_name=config.primary_provider.name,
            provider_model=config.primary_provider.model,
            usage=usage,
            escalation_reason=last_reason,
            approval_request=approval,
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
            local_attempts=max(1, config.retry_policy.local_max_attempts),
        )

    return GenerationOutcome(
        status="needs_review",
        sections=None,
        provider_name=config.primary_provider.name,
        provider_model=config.primary_provider.model,
        escalation_reason=last_reason,
        keyword_targets=keyword_targets,
        keyword_tags=keyword_tags,
        local_attempts=max(1, config.retry_policy.local_max_attempts),
    )


def run_approved_fallback(
    config: AppConfig,
    entry: BibliographyEntry,
    extracted_text: str,
    bibliography: BibliographyIndex,
    approval_request: ApprovalRequest,
    keyword_targets: list[str],
    keyword_tags: list[str],
) -> GenerationOutcome:
    fallback = next((item for item in config.fallback_providers if item.name == approval_request.fallback_provider), None)
    if fallback is None:
        return GenerationOutcome(
            status="needs_review",
            sections=None,
            provider_name=config.primary_provider.name,
            provider_model=config.primary_provider.model,
            escalation_reason="approved fallback provider not configured",
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
        )

    try:
        sections = _run_provider(fallback, config, entry, extracted_text, bibliography, keyword_targets)
        valid, reason = _validate_sections(sections)
        if not valid:
            return GenerationOutcome(
                status="needs_review",
                sections=None,
                provider_name=fallback.name,
                provider_model=fallback.model,
            usage=approval_request.usage,
            escalation_reason=reason,
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
            local_attempts=0,
        )
        sections = _apply_keyword_enrichment(sections, keyword_targets, keyword_tags)
        record_spend(config.budget_ledger_file, approval_request.usage, entry.citekey)
        return GenerationOutcome(
            status="success",
            sections=sections,
            provider_name=fallback.name,
            provider_model=fallback.model,
            usage=approval_request.usage,
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
            local_attempts=0,
        )
    except (RuntimeError, urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
        return GenerationOutcome(
            status="needs_review",
            sections=None,
            provider_name=fallback.name,
            provider_model=fallback.model,
            usage=approval_request.usage,
            escalation_reason=str(exc),
            keyword_targets=keyword_targets,
            keyword_tags=keyword_tags,
            local_attempts=0,
        )
