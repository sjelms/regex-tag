from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig, KeywordPolicyConfig
from .utils import dedupe_casefold, normalize_text

INSTITUTION_MARKERS = (
    "university",
    "college",
    "school",
    "association",
    "institute",
    "society",
    "department",
    "press",
    "council",
    "academy",
    "organization",
)
GEOGRAPHY_MARKERS = (
    "london",
    "washington",
    "boston",
    "oxford",
    "paris",
    "europe",
    "africa",
    "asia",
    "america",
    "australia",
)
INFRASTRUCTURE_MARKERS = (
    "world wide web",
    "website",
    "internet",
    "jstor",
    "doi",
)


@dataclass
class KeywordEntry:
    alias: str
    target: str
    clusters: list[str]


@dataclass
class KeywordCatalogue:
    unambiguous: dict[str, KeywordEntry]
    ambiguous: list[dict[str, object]]


@dataclass
class KeywordEnrichment:
    guidance_targets: list[str]
    metadata_links: list[str]
    metadata_tags: list[str]


def _clean_csv_value(value: str) -> str:
    cleaned = (value or "").strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) >= 2:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def load_keyword_catalogue(config: AppConfig) -> KeywordCatalogue | None:
    policy = config.keyword_policy
    if not policy.enabled or policy.unambiguous_csv is None or not policy.unambiguous_csv.exists():
        return None

    unambiguous: dict[str, KeywordEntry] = {}
    with policy.unambiguous_csv.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            alias = _clean_csv_value(row.get("Alias") or "")
            target = _clean_csv_value(row.get("LinkTarget") or "")
            if not alias or not target:
                continue
            clusters = dedupe_casefold(
                [_clean_csv_value(cluster) for cluster in (row.get("Clusters") or "").split(";") if cluster.strip()]
            )
            unambiguous[alias] = KeywordEntry(alias=alias, target=target, clusters=clusters)

    ambiguous: list[dict[str, object]] = []
    if policy.ambiguous_json and policy.ambiguous_json.exists():
        with policy.ambiguous_json.open("r", encoding="utf-8") as handle:
            ambiguous = json.load(handle)

    return KeywordCatalogue(unambiguous=unambiguous, ambiguous=ambiguous)


def _count_alias_matches(text: str, alias: str) -> int:
    pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _is_stop_target(entry: KeywordEntry) -> bool:
    target_norm = normalize_text(entry.target)
    cluster_norms = {normalize_text(cluster) for cluster in entry.clusters}
    if "organizations institutions" in cluster_norms:
        return True
    if "geography regions" in cluster_norms:
        return True
    if any(marker in target_norm for marker in INSTITUTION_MARKERS):
        return True
    if any(marker in target_norm for marker in GEOGRAPHY_MARKERS):
        return True
    if any(marker in target_norm for marker in INFRASTRUCTURE_MARKERS):
        return True
    return False


def _general_only(entry: KeywordEntry) -> bool:
    cluster_norms = {normalize_text(cluster) for cluster in entry.clusters if cluster.strip()}
    return not cluster_norms or cluster_norms == {"general"}


def enrich_keywords(
    text: str,
    catalogue: KeywordCatalogue | None,
    policy: KeywordPolicyConfig,
    title: str = "",
    abstract: str = "",
) -> KeywordEnrichment:
    if catalogue is None or not text:
        return KeywordEnrichment(guidance_targets=[], metadata_links=[], metadata_tags=[])

    title_abstract = f"{title}\n{abstract}"
    counts: Counter[str] = Counter()
    metadata_eligible: list[str] = []
    cluster_tags: dict[str, set[str]] = {}

    for alias, entry in catalogue.unambiguous.items():
        matches = _count_alias_matches(text, alias)
        if not matches:
            continue
        counts[entry.target] += matches
        cluster_tags.setdefault(entry.target, set()).update(entry.clusters)

        title_hits = _count_alias_matches(title_abstract, alias)
        if _is_stop_target(entry):
            continue
        if _general_only(entry) and title_hits == 0:
            continue
        if len(normalize_text(entry.target).split()) <= 1 and title_hits == 0:
            continue
        if title_hits > 0 or matches >= max(1, policy.min_body_matches):
            metadata_eligible.append(entry.target)

    guidance_targets = [target for target, _count in counts.most_common(policy.max_guidance_terms)]
    metadata_links = dedupe_casefold(metadata_eligible)[:policy.max_see_also_links]
    metadata_tags: list[str] = []
    for target in metadata_links:
        metadata_tags.append(target)
        for cluster in sorted(cluster_tags.get(target, set())):
            if normalize_text(cluster) == "general":
                continue
            if cluster not in metadata_tags:
                metadata_tags.append(cluster)
            if len(metadata_tags) >= policy.max_metadata_tags:
                break
        if len(metadata_tags) >= policy.max_metadata_tags:
            break

    return KeywordEnrichment(
        guidance_targets=guidance_targets,
        metadata_links=metadata_links,
        metadata_tags=metadata_tags[:policy.max_metadata_tags],
    )
