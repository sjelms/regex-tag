
import csv
import re

def generate_keyword_mappings(term_file_path, csv_output_path):
    """
    Parses a term file and generates a CSV mapping aliases to link targets.

    - Reads a flat list of terms.
    - The full line is the LinkTarget (filename).
    - Extracts aliases from parentheses, e.g., "Term (Alias)".
    - Resolves conflicts by prioritizing longer, more descriptive LinkTargets.
    """
    mappings = {}

    try:
        with open(term_file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Term file not found at {term_file_path}")
        return

    # Sort by length descending to ensure longer targets are processed first,
    # which helps in resolving alias conflicts correctly.
    lines.sort(key=len, reverse=True)

    for line in lines:
        link_target = line
        aliases = {line}

        # Regex to find content in parentheses
        match = re.search(r'^(.*) \((.*)\)$', line)
        if match:
            term_without_alias = match.group(1).strip()
            alias_in_parens = match.group(2).strip()
            aliases.add(term_without_alias)
            aliases.add(alias_in_parens)

        for alias in aliases:
            # The sort key ensures that if an alias exists, it will only be
            # overwritten by a more descriptive (longer) link target.
            if alias not in mappings:
                 mappings[alias] = link_target

    # Write to CSV
    try:
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Alias', 'LinkTarget'])
            for alias, target in sorted(mappings.items()):
                writer.writerow([alias, target])
    except IOError as e:
        print(f"Error writing to CSV file {csv_output_path}: {e}")

