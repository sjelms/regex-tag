
import csv
import itertools
import json
import re
from collections import defaultdict
from typing import Dict, List, Set

CONNECTOR_VARIATIONS = {
    "-": ["-", " ", "/"],
    "–": ["–", "-", " ", "/"],
    "—": ["—", "-", " ", "/"],
    "/": ["/", "-", " "],
}


def _collapse_spaces(value: str) -> str:
    """Normalize whitespace by collapsing multiple spaces and trimming ends."""
    return re.sub(r"\s+", " ", value.strip())


def _generate_alias_variations(alias: str) -> Set[str]:
    """
    Produce simple punctuation variations for an alias to catch hyphen/slash swaps.
    """
    alias = alias.strip()
    if not alias:
        return set()

    variations: Set[str] = {_collapse_spaces(alias)}

    connector_positions = [(idx, char) for idx, char in enumerate(alias) if char in CONNECTOR_VARIATIONS]
    if connector_positions:
        chars = list(alias)
        options = [CONNECTOR_VARIATIONS[char] for _, char in connector_positions]
        for replacements in itertools.product(*options):
            trial = chars[:]
            for (idx, _), replacement in zip(connector_positions, replacements):
                trial[idx] = replacement
            variations.add(_collapse_spaces("".join(trial)))

    # Include a version with connectors removed entirely when appropriate.
    stripped = re.sub(r"[-–—/]", " ", alias)
    variations.add(_collapse_spaces(stripped))

    return {variant for variant in variations if variant}


def generate_keyword_mappings(
    term_file_path: str,
    unambiguous_csv_output_path: str,
    ambiguous_json_output_path: str,
) -> None:
    """
    Parses a term file and generates a CSV mapping aliases to link targets.

    This function reads a flat text file where each line is a term. It processes
    these terms to create a mapping from various aliases to a canonical link target,
    which is the term as it appears on the line (matching a filename).

    - Reads a flat list of terms.
    - The full line is the LinkTarget (filename).
    - Extracts aliases from parentheses, e.g., "Term (Alias)".
    - Resolves alias conflicts by prioritizing the longest, most descriptive LinkTarget.

    Args:
        term_file_path (str): The absolute path to the input term list file.
        csv_output_path (str): The absolute path for the output CSV mapping file.
    """
    alias_to_targets: Dict[str, Set[str]] = defaultdict(set)
    alias_to_source_terms: Dict[str, Set[str]] = defaultdict(set)

    try:
        with open(term_file_path, 'r', encoding='utf-8') as f:
            lines: List[str] = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Term file not found at {term_file_path}")
        return

    for line in lines:
        link_target: str = line
        aliases: Set[str] = {line}

        # Regex to find content in parentheses, e.g., "Term (Alias)"
        match = re.search(r'^(.*) \((.*)\)$', line)
        if match:
            term_without_alias: str = match.group(1).strip()
            alias_in_parens: str = match.group(2).strip()
            aliases.add(term_without_alias)
            aliases.add(alias_in_parens)

        expanded_aliases: Set[str] = set()
        for alias in aliases:
            expanded_aliases.update(_generate_alias_variations(alias))

        for alias in expanded_aliases:
            alias_to_targets[alias].add(link_target)
            alias_to_source_terms[alias].add(line)

    unambiguous_mappings: Dict[str, str] = {}
    ambiguous_entries: List[Dict[str, object]] = []

    for alias, targets in alias_to_targets.items():
        if len(targets) == 1:
            unambiguous_mappings[alias] = next(iter(targets))
        else:
            ambiguous_entries.append({
                "alias": alias,
                "candidates": sorted(targets),
                "source_terms": sorted(alias_to_source_terms.get(alias, [])),
            })

    # Write unambiguous mappings to CSV
    try:
        with open(unambiguous_csv_output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Alias', 'LinkTarget'])
            # Sort by alias for consistent output
            for alias, target in sorted(unambiguous_mappings.items()):
                writer.writerow([alias, target])
        print(f"✅ Success! Wrote {len(unambiguous_mappings)} unambiguous keyword mappings to '{unambiguous_csv_output_path}'")
    except IOError as e:
        print(f"Error writing to CSV file {unambiguous_csv_output_path}: {e}")

    # Write ambiguous mappings to JSON
    try:
        with open(ambiguous_json_output_path, 'w', encoding='utf-8') as f:
            json.dump(sorted(ambiguous_entries, key=lambda item: item["alias"]), f, indent=2, ensure_ascii=False)
        print(f"✅ Success! Wrote {len(ambiguous_entries)} ambiguous keyword entries to '{ambiguous_json_output_path}'")
    except IOError as e:
        print(f"Error writing to JSON file {ambiguous_json_output_path}: {e}")
