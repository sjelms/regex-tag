import os
import re
import json

from .config_loader import load_config

def load_authors(filepath):
    """Loads the author data from the JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Sort authors by length of full name, longest first.
            # This prevents "John Smith" from being replaced before "John Smith Jr."
            authors = json.load(f)
            authors.sort(key=lambda x: len(x['fullName']), reverse=True)
            return authors
    except FileNotFoundError:
        print(f"Error: Author data file '{filepath}' not found.")
        return []

def process_markdown_file(filepath, authors):
    """
    Reads a markdown file, replaces author names with Obsidian links, and saves it back.
    Returns True if the file was changed, False otherwise.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"  -> Could not read file: {e}")
        return False

    content = original_content

    for author in authors:
        full_name = author['fullName']
        last_name = author['lastName']
        
        # --- Rule 1: Replace Full Name ---
        # Search for the full name, but not if it's already part of a link [[...]]
        # or immediately preceded by an @ (for citation keys).
        # We use word boundaries (\b) to avoid matching parts of words.
        full_name_pattern = r'(?<!\[\[)(?<!@)\b' + re.escape(full_name) + r'\b(?!\||\]\])'
        content = re.sub(full_name_pattern, f'[[{full_name}]]', content)

        # --- Rule 2: Replace Last Name with Alias ---
        # Search for the last name alone.
        # This is more complex to avoid replacing it inside the full name or other contexts.
        # Negative lookbehind (?<!) ensures it's not preceded by a letter (part of another word) or @.
        # Negative lookahead (?!) ensures it's not followed by a letter, |, or ]].
        last_name_pattern = r'(?<![\w@\[])\b' + re.escape(last_name) + r'\b(?![\w\|\]])'
        content = re.sub(last_name_pattern, f'[[{full_name}|{last_name}]]', content)
        
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
    """Main function to orchestrate the linking process."""
    print("Starting author linking process...")
    
    config = load_config()
    if not config:
        return

    scan_directories = config.get('scan_directories', [])
    authors_json_file = config.get('authors_json_file')

    if not scan_directories or not authors_json_file:
        print("Error: 'scan_directories' or 'authors_json_file' not set in config.yaml. Exiting.")
        return

    authors = load_authors(authors_json_file)
    if not authors:
        print("No authors loaded from authors.json. Exiting.")
        return
        
    print(f"Loaded {len(authors)} authors. Scanning directories...")
    
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
                    if process_markdown_file(filepath, authors):
                        modified_files_count += 1
                        print(" -> Linked!")
                    else:
                        print(" -> No changes.")
                        
    print("\n--- Process Complete ---")
    print(f"Scanned {total_files_scanned} Markdown files.")
    print(f"Modified {modified_files_count} files.")
    print("------------------------")


if __name__ == "__main__":
    main()
