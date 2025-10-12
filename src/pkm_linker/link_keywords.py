
import os
import re
import csv
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None


def _strip_quotes(value: str) -> str:
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _fallback_parse(content: str) -> Dict[str, Any]:
    """
    Minimal parser that understands the limited YAML subset used in config.yaml.
    Supports string values and top-level lists defined with "- item" syntax.
    """
    config: Dict[str, Any] = {}
    current_list_key: Optional[str] = None

    for raw_line in content.splitlines():
        line = raw_line.split('#', 1)[0].rstrip()
        if not line.strip():
            continue

        if line.lstrip().startswith('- '):
            if not current_list_key:
                raise ValueError(f"List item without a key in config: '{raw_line}'")
            item = _strip_quotes(line.lstrip()[2:].strip())
            config.setdefault(current_list_key, []).append(item)
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if value:
                config[key] = _strip_quotes(value)
                current_list_key = None
            else:
                config[key] = []
                current_list_key = key
            continue

        raise ValueError(f"Unable to parse config line: '{raw_line}'")

    return config

# --- Configuration ---
CONFIG_FILE = "config.yaml"

def load_config():
    """Loads configuration from the YAML file."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if yaml:
                return yaml.safe_load(content)
            return _fallback_parse(content)
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        return None
    except ValueError as exc:
        print(f"Error parsing configuration file '{CONFIG_FILE}': {exc}")
        return None

def load_keywords(filepath):
    """Loads keywords from a CSV file."""
    keywords = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip the header row
            for row in reader:
                if len(row) >= 2:
                    # The 'search' term is the Alias, 'replace' is the LinkTarget
                    keywords.append({'search': row[0], 'replace': row[1]})
        
        # Sort keywords by the length of the search term, longest first.
        # This prevents "MIT" from matching before "MIT Sloan School of Management".
        keywords.sort(key=lambda x: len(x['search']), reverse=True)
        return keywords
    except FileNotFoundError:
        print(f"Error: Keyword file not found at '{filepath}'")
        return []

def process_markdown_file(filepath, keywords):
    """
    Reads a markdown file, replaces keywords with Obsidian links, and saves it back.
    Returns True if the file was changed, False otherwise.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"  -> Could not read file: {e}")
        return False

    content = original_content

    for keyword in keywords:
        search_term = keyword['search']
        link_target = keyword['replace']
        
        # Regex to find the search term as a whole word, but not if it's already part of a wiki-link.
        pattern = r'(?<!\[\[)\\b' + re.escape(search_term) + r'\\b(?![\|\|\|]])'

        # Determine the replacement format.
        if search_term.lower() == link_target.lower():
            # If the found term is the same as the target, create a direct link.
            replacement = f'[[{link_target}]]'
        else:
            # If the found term is an alias, create a piped link.
            replacement = f'[[{link_target}|{search_term}]]'
        
        # Use a function for replacement to handle case preservation of the found term
        def create_replacement(match):
            found_term = match.group(0)
            if found_term.lower() == link_target.lower():
                return f'[[{link_target}]]'
            else:
                return f'[[{link_target}|{found_term}]]'

        content = re.sub(pattern, create_replacement, content, flags=re.IGNORECASE)
        
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"  -> Could not write to file: {e}")
            return False
            
    return False

def main():
    """Main function to orchestrate the keyword linking process."""
    print("Starting keyword linking process...")
    
    config = load_config()
    if not config:
        return

    scan_directories = config.get('scan_directories', [])
    keywords_file = config.get('keywords_csv_file')

    if not scan_directories or not keywords_file:
        print("Error: 'scan_directories' or 'keywords_csv_file' not set in config.yaml. Exiting.")
        return

    keywords = load_keywords(keywords_file)
    if not keywords:
        print("No keywords loaded. Exiting.")
        return
        
    print(f"Loaded {len(keywords)} keywords. Scanning directories...")
    
    modified_files_count = 0
    total_files_scanned = 0

    for directory in scan_directories:
        if not os.path.isdir(directory):
            print(f"\nWarning: Directory not found, skipping: {directory}")
            continue
            
        print(f"\nScanning directory: {directory}")
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.md'):
                    total_files_scanned += 1
                    filepath = os.path.join(root, filename)
                    print(f"- Processing: {filename}", end='')
                    if process_markdown_file(filepath, keywords):
                        modified_files_count += 1
                        print(" -> Linked!")
                    else:
                        print(" -> No changes.")
                        
    print("\n--- Process Complete ---")
    print(f"Scanned {total_files_scanned} Markdown files.")
    print(f"Modified {modified_files_count} files with new keyword links.")
    print("------------------------")


if __name__ == "__main__":
    main()
