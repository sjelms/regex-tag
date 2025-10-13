import os
import csv
import yaml

from pathlib import Path

CONFIG_FILE = "config.yaml"
DEFAULT_OUTPUT_CSV = "unambiguous-keywords.csv"


def load_config():
    """Return configuration as a dict or None on failure."""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
    except yaml.YAMLError as exc:
        print(f"Error parsing '{CONFIG_FILE}': {exc}")
    return None


def resolve_directories(raw_dirs):
    """Expand environment variables and ~ for each configured directory."""
    directories = []
    for entry in raw_dirs:
        if not entry:
            continue
        expanded = os.path.expandvars(os.path.expanduser(str(entry)))
        directories.append(Path(expanded))
    return directories

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
    config = load_config()
    if not config:
        return

    raw_dirs = config.get("tag_extract_directories") or config.get("scan_directories")
    if not raw_dirs:
        print("Error: Set 'tag_extract_directories' (or 'scan_directories') in config.yaml.")
        return

    directories = resolve_directories(raw_dirs)
    output_path = Path(config.get("keyword_output_csv", DEFAULT_OUTPUT_CSV))

    rows = []

    for dir_path in directories:
        if not dir_path.is_dir():
            print(f"Warning: Directory not found, skipping: {dir_path}")
            continue

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
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["search_term", "canonical_term", "file", "see_also", "tags", "note_excerpt"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Extracted {len(rows)} keyword mappings into {output_path}")

if __name__ == "__main__":
    main()
