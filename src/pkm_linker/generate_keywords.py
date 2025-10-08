import csv
import re
from typing import Dict, List, Set

def generate_keyword_mappings(term_file_path: str, csv_output_path: str) -> None:
    """
    Parses a term file and generates a CSV mapping aliases to link targets.

    This function reads a flat text file where each line is a term. It processes
    these terms to create a mapping from various aliases to a canonical link target,
    which is the term as it appears on the line (matching a filename).

    - Reads a flat list of terms.
    - The full line is the LinkTarget (filename).
    - Extracts aliases from parentheses, e.g., "Term (Alias)".
    - Resolves alias conflicts by prioritizing longer, more descriptive LinkTargets.

    Args:
        term_file_path (str): The absolute path to the input term list file.
        csv_output_path (str): The absolute path for the output CSV mapping file.
    """
    mappings: Dict[str, str] = {}

    try:
        with open(term_file_path, 'r', encoding='utf-8') as f:
            lines: List[str] = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Term file not found at {term_file_path}")
        return

    # Sort by length descending to ensure longer targets are processed first,
    # which helps in resolving alias conflicts correctly.
    lines.sort(key=len, reverse=True)

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

        for alias in aliases:
            # The sort key on `lines` ensures that if an alias exists, it will only be
            # overwritten by a more descriptive (longer) link target.
            if alias not in mappings:
                 mappings[alias] = link_target

    # Write to CSV
    try:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Alias', 'LinkTarget'])
            # Sort by alias for consistent output
            for alias, target in sorted(mappings.items()):
                writer.writerow([alias, target])
        print(f"✅ Success! Wrote {len(mappings)} keyword mappings to '{csv_output_path}'")
    except IOError as e:
        print(f"Error writing to CSV file {csv_output_path}: {e}")