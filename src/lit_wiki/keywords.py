from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import AppConfig


@dataclass
class KeywordCatalogue:
    unambiguous: dict[str, dict[str, object]]
    ambiguous: list[dict[str, object]]


def load_keyword_catalogue(config: AppConfig) -> KeywordCatalogue | None:
    policy = config.keyword_policy
    if not policy.enabled or policy.unambiguous_csv is None or not policy.unambiguous_csv.exists():
        return None

    unambiguous: dict[str, dict[str, object]] = {}
    with policy.unambiguous_csv.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            alias = (row.get("Alias") or "").strip()
            if not alias:
                continue
            unambiguous[alias] = {
                "target": (row.get("LinkTarget") or "").strip(),
                "clusters": [cluster.strip() for cluster in (row.get("Clusters") or "").split(";") if cluster.strip()],
            }

    ambiguous: list[dict[str, object]] = []
    if policy.ambiguous_json and policy.ambiguous_json.exists():
        with policy.ambiguous_json.open("r", encoding="utf-8") as handle:
            ambiguous = json.load(handle)

    return KeywordCatalogue(unambiguous=unambiguous, ambiguous=ambiguous)


def enrich_keywords(text: str, catalogue: KeywordCatalogue | None, max_links: int = 10) -> tuple[list[str], list[str]]:
    if catalogue is None or not text:
        return [], []

    counts: Counter[str] = Counter()
    matched_tags: set[str] = set()
    for alias, payload in catalogue.unambiguous.items():
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if not matches:
            continue
        target = str(payload.get("target", "")).strip()
        if not target:
            continue
        counts[target] += len(matches)
        matched_tags.add(target)
        for cluster in payload.get("clusters", []):
            matched_tags.add(str(cluster))

    ordered_targets = [target for target, _count in counts.most_common(max_links)]
    return ordered_targets, sorted(matched_tags)
