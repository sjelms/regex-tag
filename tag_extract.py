import os
import csv
import yaml

from pathlib import Path

# Paths
dirs = [
    "/Users/stephenelms/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/Library Database/Terminology",
    "/Users/stephenelms/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault/Tags",
]

output_csv = "keyword-mapping.csv"

def extract_yaml_and_body(md_path):
    """Parse YAML frontmatter and return metadata + note body."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    if text.startswith("---"):
        _, yaml_block, body = text.split("---", 2)
        metadata = yaml.safe_load(yaml_block) or {}
    else:
        metadata, body = {}, text

    return metadata, body.strip()

def main():
    rows = []

    for dir_path in dirs:
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".md"):
                    md_path = Path(root) / file
                    metadata, body = extract_yaml_and_body(md_path)

                    term = metadata.get("term", file.replace(".md", ""))
                    aliases = metadata.get("aliases", [])
                    see_also = metadata.get("see also", [])
                    tags = metadata.get("tags", [])

                    # Simple body excerpt (first 250 chars)
                    excerpt = body.replace("\n", " ").strip()[:250]

                    # Build rows: one per alias, plus canonical form
                    search_terms = aliases if aliases else []
                    search_terms.append(term)

                    for alias in search_terms:
                        rows.append({
                            "search_term": alias,
                            "canonical_term": term,
                            "file": file,
                            "see_also": "; ".join(see_also) if isinstance(see_also, list) else see_also,
                            "tags": "; ".join(tags) if isinstance(tags, list) else tags,
                            "note_excerpt": excerpt
                        })

    # Write to CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["search_term", "canonical_term", "file", "see_also", "tags", "note_excerpt"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Extracted {len(rows)} keyword mappings into {output_csv}")

if __name__ == "__main__":
    main()